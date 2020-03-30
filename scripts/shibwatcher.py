import logging
import logging.config
import os
import sys
import tarfile
import time
from hashlib import md5
from tempfile import TemporaryFile

import docker
from kubernetes import client, config
from kubernetes.stream import stream

from settings import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("shibwatcher")


class BaseClient(object):
    def get_oxshibboleth_containers(self):
        """Gets oxShibboleth containers.
        Subclass __MUST__ implement this method.
        """
        raise NotImplementedError

    def get_container_ip(self, container):
        """Gets container's IP address.
        Subclass __MUST__ implement this method.
        """
        raise NotImplementedError

    def get_container_name(self, container):
        """Gets container's IP address.
        Subclass __MUST__ implement this method.
        """
        raise NotImplementedError

    def copy_to_container(self, container, path):
        """Gets container's IP address.
        Subclass __MUST__ implement this method.
        """
        raise NotImplementedError


class DockerClient(BaseClient):
    def __init__(self, base_url="unix://var/run/docker.sock"):
        self.client = docker.DockerClient(base_url=base_url)

    def get_oxshibboleth_containers(self):
        return self.client.containers.list(filters={'label': 'APP_NAME=oxshibboleth'})

    def get_container_ip(self, container):
        for _, network in container.attrs["NetworkSettings"]["Networks"].iteritems():
            return network["IPAddress"]

    def get_container_name(self, container):
        return container.name

    def copy_to_container(self, container, path):
        src = os.path.basename(path)
        dirname = os.path.dirname(path)

        os.chdir(dirname)

        with tarfile.open(src + ".tar", "w:gz") as tar:
            tar.add(src)

        with open(src + ".tar", "rb") as f:
            payload = f.read()

            # create directory first
            container.exec_run("mkdir -p {}".format(dirname))

            # copy file
            container.put_archive(os.path.dirname(path), payload)

        try:
            os.unlink(src + ".tar")
        except OSError:
            pass


class KubernetesClient(BaseClient):
    def __init__(self):
        config_loaded = False

        try:
            config.load_incluster_config()
            config_loaded = True
        except config.config_exception.ConfigException:
            logger.warn("Unable to load in-cluster configuration; trying to load from Kube config file")
            try:
                config.load_kube_config()
                config_loaded = True
            except (IOError, config.config_exception.ConfigException) as exc:
                logger.warn("Unable to load Kube config; reason={}".format(exc))

        if not config_loaded:
            logger.error("Unable to load in-cluster or Kube config")
            sys.exit(1)

        cli = client.CoreV1Api()
        cli.api_client.configuration.assert_hostname = False
        self.client = cli

    def get_oxshibboleth_containers(self):
        return self.client.list_pod_for_all_namespaces(
            label_selector='APP_NAME=oxshibboleth'
        ).items

    def get_container_ip(self, container):
        return container.status.pod_ip

    def get_container_name(self, container):
        return container.metadata.name

    def copy_to_container(self, container, path):
        # make sure parent directory is created first
        resp = stream(
            self.client.connect_get_namespaced_pod_exec,
            container.metadata.name,
            container.metadata.namespace,
            command=["/bin/sh", "-c", "mkdir -p {}".format(os.path.dirname(path))],
            stderr=True,
            stdin=True,
            stdout=True,
            tty=False,
        )

        # copy file implementation
        resp = stream(
            self.client.connect_get_namespaced_pod_exec,
            container.metadata.name,
            container.metadata.namespace,
            command=["tar", "xvf", "-", "-C", "/"],
            stderr=True,
            stdin=True,
            stdout=True,
            tty=False,
            _preload_content=False,
        )

        with TemporaryFile() as tar_buffer:
            with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
                tar.add(path)

            tar_buffer.seek(0)
            commands = []
            commands.append(tar_buffer.read())

            while resp.is_open():
                resp.update(timeout=1)
                if resp.peek_stdout():
                    # logger.info("STDOUT: %s" % resp.read_stdout())
                    pass
                if resp.peek_stderr():
                    # logger.info("STDERR: %s" % resp.read_stderr())
                    pass
                if commands:
                    c = commands.pop(0)
                    resp.write_stdin(c)
                else:
                    break
            resp.close()


class ShibWatcher(object):
    filepath_mods = {}
    oxshibboleth_nums = 0

    def __init__(self):
        metadata = os.environ.get("GLUU_CONTAINER_METADATA", "docker")

        if metadata == "kubernetes":
            self.client = KubernetesClient()
        else:
            self.client = DockerClient()

    @property
    def rootdir(self):
        return "/opt/shibboleth-idp"

    @property
    def patterns(self):
        return [".xml", ".config", ".xsd", ".dtd"]

    def sync_to_oxshibboleth(self, filepaths):
        """Sync modified files to all oxShibboleth.
        """
        containers = self.client.get_oxshibboleth_containers()

        if not containers:
            logger.warn("Unable to find any oxShibboleth container; make sure "
                        "to deploy oxShibboleth and set APP_NAME=oxshibboleth "
                        "label on container level")
            return

        for container in containers:
            for filepath in filepaths:
                logger.info("Copying {} to {}:{}".format(filepath, self.client.get_container_name(container), filepath))
                self.client.copy_to_container(container, filepath)

    def get_filepaths(self):
        filepaths = []

        for subdir, _, files in os.walk(self.rootdir):
            for file_ in files:
                filepath = os.path.join(subdir, file_)

                if os.path.splitext(filepath)[-1] not in self.patterns:
                    continue
                filepaths.append(filepath)
        return filepaths

    def sync_by_digest(self, filepaths):
        _filepaths = []

        for filepath in filepaths:
            with open(filepath) as f:
                digest = md5(f.read()).hexdigest()

            # skip if nothing has been tampered
            if filepath in self.filepath_mods and digest == self.filepath_mods[filepath]:
                continue

            # _filepath_mods[filepath] = digest
            _filepaths.append(filepath)
            self.filepath_mods[filepath] = digest

        # nothing changed
        if not _filepaths:
            return False

        logger.info("Sync modified files to oxShibboleth ...")
        self.sync_to_oxshibboleth(_filepaths)
        return True

    def maybe_sync(self):
        try:
            shib_nums = len(self.client.get_oxshibboleth_containers())
            # logger.info("Saved shib nums: " + str(self.oxshibboleth_nums))
            # logger.info("Current shib nums: " + str(shib_nums))

            filepaths = self.get_filepaths()

            if self.sync_by_digest(filepaths):
                # keep the number of registered oxshibboleth for later check
                self.oxshibboleth_nums = shib_nums
                return

            # check again in case we have new oxshibboleth container
            shib_nums = len(self.client.get_oxshibboleth_containers())

            # probably scaled up
            if shib_nums > self.oxshibboleth_nums:
                logger.info("Sync files to oxShibboleth ...")
                self.sync_to_oxshibboleth(filepaths)

            # keep the number of registered oxshibboleth
            self.oxshibboleth_nums = shib_nums
        except Exception as exc:
            logger.warn("Got unhandled exception; reason={}".format(exc))


def get_sync_interval():
    default_interval = 10
    try:
        sync_interval = int(os.environ.get("GLUU_SHIBWATCHER_INTERVAL", default_interval))
    except ValueError:
        sync_interval = default_interval
    finally:
        if sync_interval < 1:
            sync_interval = default_interval
    return sync_interval


if __name__ == "__main__":
    try:
        # time.sleep(30)
        sync_interval = get_sync_interval()
        watcher = ShibWatcher()

        while True:
            watcher.maybe_sync()
            time.sleep(sync_interval)
    except KeyboardInterrupt:
        logger.warn("Cancelled by user ... exiting")

import logging
import logging.config
import os
import sys
import tarfile
import time
from tempfile import TemporaryFile

import click
import docker
from kubernetes import client, config
from kubernetes.stream import stream
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from pygluu.containerlib.utils import as_boolean

from settings import LOGGING_CONFIG

PATTERNS = (
    "*.xml",
    "*.config",
    "*.xsd",
    "*.dtd",
)

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

    def delete_from_container(self, container, path):
        container.exec_run("rm -f {}".format(path))


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

    def delete_from_container(self, container, path):
        stream(
            self.client.connect_get_namespaced_pod_exec,
            container.metadata.name,
            container.metadata.namespace,
            command=["/bin/sh", "-c", "rm -f {}".format(path)],
            stderr=True,
            stdin=True,
            stdout=True,
            tty=False,
        )


class ClientMixin(object):
    def __init__(self):
        metadata = os.environ.get("GLUU_CONTAINER_METADATA", "docker")

        if metadata == "kubernetes":
            self.client = KubernetesClient()
        else:
            self.client = DockerClient()


class ContainerHandler(ClientMixin):
    filepath_mods = {}
    oxshibboleth_nums = 0

    @property
    def rootdir(self):
        return "/opt/shibboleth-idp"

    @property
    def patterns(self):
        return [os.path.splitext(pattern)[-1] for pattern in PATTERNS]

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

    def maybe_sync(self):
        shib_nums = len(self.client.get_oxshibboleth_containers())

        # probably scaled up
        if shib_nums > self.oxshibboleth_nums:
            logger.info("Sync files to oxShibboleth ...")
            filepaths = self.get_filepaths()
            self.sync_to_oxshibboleth(filepaths)

        # keep the number of registered oxshibboleth
        self.oxshibboleth_nums = shib_nums


class FilesystemHandler(PatternMatchingEventHandler, ClientMixin):
    def on_moved(self, event):
        # callback when files are moved from /opt/shibboleth-idp/temp_metadata
        # to /opt/shibboleth-idp/metadata
        self.copy_file(event.src_path, event.dest_path)

    def on_modified(self, event):
        # destination equals source path
        self.copy_file(event.src_path, event.src_path)

    def on_deleted(self, event):
        # callback when files are deleted from /opt/shibboleth-idp/temp_metadata
        self.delete_file(event.src_path)

    def copy_file(self, src, dest):
        containers = self.client.get_oxshibboleth_containers()

        if not containers:
            logger.warn("Unable to find any oxShibboleth container; make sure "
                        "to deploy oxShibboleth and set APP_NAME=oxshibboleth "
                        "label on container level")
            return

        for container in containers:
            logger.info("Copying {} to {}:{}".format(src, self.client.get_container_name(container), dest))
            self.client.copy_to_container(container, dest)

    def delete_file(self, src):
        containers = self.client.get_oxshibboleth_containers()

        if not containers:
            logger.warn("Unable to find any oxShibboleth container; make sure "
                        "to deploy oxShibboleth and set APP_NAME=oxshibboleth "
                        "label on container level")
            return

        for container in containers:
            logger.info("Deleting {}:{}".format(self.client.get_container_name(container), src))
            self.client.delete_from_container(container, src)


@click.group()
def cli():
    pass


@cli.command("watch-files")
def watch_files():
    """Watch events on Shibboleth-related files.
    """
    enable_sync = as_boolean(
        os.environ.get("GLUU_SYNC_SHIB_MANIFESTS", False)
    )
    if not enable_sync:
        logger.warn("Sync Shibboleth files are disabled ... exiting")
        raise click.Abort()

    event_handler = FilesystemHandler(patterns=PATTERNS)
    observer = Observer()
    observer.schedule(event_handler, "/opt/shibboleth-idp", recursive=True)
    observer.start()

    # The above starts an observing thread, so the main thread can just wait
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
        logger.warn("Canceled by user ... exiting")
    except Exception as exc:
        logger.warn("Got unhandled exception; reason={}".format(exc))
    observer.join()


@cli.command("watch-containers")
def watch_containers():
    """Watch events on Shibboleth containers in the cluster.
    """
    enable_sync = as_boolean(
        os.environ.get("GLUU_SYNC_SHIB_MANIFESTS", False)
    )
    if not enable_sync:
        logger.warn("Sync Shibboleth files are disabled ... exiting")
        raise click.Abort()

    try:
        sync_interval = get_sync_interval()
        watcher = ContainerHandler()

        while True:
            watcher.maybe_sync()
            time.sleep(sync_interval)
    except KeyboardInterrupt:
        logger.warn("Canceled by user ... exiting")
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
    cli()

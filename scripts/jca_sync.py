import subprocess
import shlex
import logging.config
import os
import time
from typing import Tuple

from settings import LOGGING_CONFIG

ROOT_DIR = "/repository/default"
SYNC_DIR = "/opt/gluu/jetty/identity/custom"

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("webdav")


def exec_cmd(cmd: str) -> Tuple[bytes, bytes, int]:
    args = shlex.split(cmd)
    popen = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = popen.communicate()
    retcode = popen.returncode
    return stdout.strip(), stderr.strip(), retcode


class RClone(object):
    def __init__(self, url, username, password):
        self.url = f"{url}/repository/default"
        self.username = username
        self.password = password

    def configure(self):
        conf_file = os.path.expanduser("~/.config/rclone/rclone.conf")
        if os.path.isfile(conf_file):
            return

        cmd = f"rclone config create jackrabbit webdav vendor other pass {self.password} user admin url {self.url}"
        _, err, code = exec_cmd(cmd)

        if code != 0:
            errors = err.decode().splitlines()
            logger.warning(f"Unable to create webdav config; reason={errors}")

    def copy_from(self, remote, local):
        cmd = f"rclone copy jackrabbit:{remote} {local} --create-empty-src-dirs"
        _, err, code = exec_cmd(cmd)

        if code != 0:
            errors = err.decode().splitlines()
            logger.debug(f"Unable to sync files from remote directories; reason={errors}")

    def copy_to(self, remote, local):
        cmd = f"rclone copy {local} jackrabbit:{remote} --create-empty-src-dirs"
        _, err, code = exec_cmd(cmd)

        if code != 0:
            errors = err.decode().splitlines()
            logger.debug(f"Unable to sync files to remote directories; reason={errors}")


def sync_from_webdav(url, username, password):
    rclone = RClone(url, username, password)
    rclone.configure()

    logger.info(f"Sync files with remote directory {url}{ROOT_DIR}{SYNC_DIR}")
    rclone.copy_from(SYNC_DIR, SYNC_DIR)


def get_sync_interval():
    default = 5 * 60  # 5 minutes

    try:
        interval = int(os.environ.get("GLUU_JCA_SYNC_INTERVAL", default))
    except ValueError:
        interval = default
    return interval


def main():
    store_type = os.environ.get("GLUU_DOCUMENT_STORE_TYPE", "LOCAL")
    if store_type != "JCA":
        logger.warning(f"Using {store_type} document store; sync is disabled ...")
        return

    url = os.environ.get("GLUU_JCA_URL", "http://localhost:8080")
    username = os.environ.get("GLUU_JCA_USERNAME", "admin")
    password = "admin"

    password_file = os.environ.get("GLUU_JCA_PASSWORD_FILE", "/etc/gluu/conf/jca_password")
    if os.path.isfile(password_file):
        with open(password_file) as f:
            password = f.read().strip()

    sync_interval = get_sync_interval()
    try:
        while True:
            sync_from_webdav(url, username, password)
            time.sleep(sync_interval)
    except KeyboardInterrupt:
        logger.warning("Canceled by user; exiting ...")


if __name__ == "__main__":
    main()

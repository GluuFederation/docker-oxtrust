import logging.config
import os
import time

from webdav3.client import Client
from webdav3.exceptions import RemoteResourceNotFound
from webdav3.exceptions import NoConnection

from settings import LOGGING_CONFIG

ROOT_DIR = "/repository/default"
SYNC_DIR = "/opt/gluu/jetty/identity/custom"

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("webdav")


def sync_from_webdav(url, username, password):
    options = {
        "webdav_hostname": url,
        "webdav_login": username,
        "webdav_password": password,
        "webdav_root": ROOT_DIR,
    }
    client = Client(options)

    try:
        logger.info(f"Sync files with remote directory {url}{ROOT_DIR}{SYNC_DIR}")
        client.pull(SYNC_DIR, SYNC_DIR)
    except (RemoteResourceNotFound, NoConnection) as exc:
        logger.warning(f"Unable to sync files from remote directory {url}{ROOT_DIR}{SYNC_DIR}; reason={exc}")


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
        logger.warn("Canceled by user; exiting ...")


if __name__ == "__main__":
    main()

# import glob
import logging.config
import os
import shutil
import tempfile
import time

from webdav3.client import Client
from webdav3.exceptions import RemoteResourceNotFound
from webdav3.exceptions import NoConnection

from settings import LOGGING_CONFIG

LOCAL_DIR = "/opt/gluu/jetty/identity/custom"
REMOTE_DIR = "".join(["repository/default", LOCAL_DIR])

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("webdav")


# def modify_identity_xml():
#     fn = "/opt/gluu/jetty/identity/webapps/identity.xml"

#     with open(fn) as f:
#         txt = f.read()

#     with open(fn, "w") as f:
#         ctx = {
#             "extra_classpath": ",".join([
#                 j.replace("/opt/gluu/jetty/identity", ".")
#                 for j in glob.iglob("/opt/gluu/jetty/identity/custom/libs/*.jar")
#             ])
#         }
#         f.write(txt % ctx)


def sync_from_webdav(url, username, password):
    options = {
        "webdav_hostname": url,
        "webdav_login": username,
        "webdav_password": password,
    }
    client = Client(options)

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            logger.info(f"Sync files from remote directory {url}/{REMOTE_DIR} into local directory {tmpdir}")

            # download remote dirs to new directory
            client.download_sync(REMOTE_DIR, tmpdir)

            # copy all downloaded files to /opt/gluu/jetty/identity/custom
            for subdir, _, files in os.walk(tmpdir):
                for file_ in files:
                    src = os.path.join(subdir, file_)
                    dest = src.replace(tmpdir, LOCAL_DIR)

                    if not os.path.exists(os.path.dirname(dest)):
                        os.makedirs(os.path.dirname(dest))

                    logger.info(f"Copying {src} to {dest}")
                    shutil.copyfile(src, dest)
        except (RemoteResourceNotFound, NoConnection) as exc:
            logger.warning(f"Unable to sync files from remote directory {url}/{REMOTE_DIR}; reason={exc}")
        # finally:
        #     modify_identity_xml()


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

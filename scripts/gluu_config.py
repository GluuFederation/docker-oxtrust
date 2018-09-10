import json
import logging
import os

import six
import kubernetes.client
import kubernetes.config
from consul import Consul

logger = logging.getLogger("gluu_config")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
fmt = logging.Formatter('%(levelname)s - %(asctime)s - %(message)s')
ch.setFormatter(fmt)
logger.addHandler(ch)

# config storage adapter
GLUU_CONFIG_ADAPTER = os.environ.get("GLUU_CONFIG_ADAPTER", "consul")

# consul host
GLUU_CONSUL_HOST = os.environ.get(
    "GLUU_CONSUL_HOST",
    # backward-compatibility; will be removed in future releases
    os.environ.get("GLUU_KV_HOST", "localhost"),
)

# consul port
GLUU_CONSUL_PORT = os.environ.get(
    "GLUU_CONSUL_PORT",
    # backward-compatibility; will be removed in future releases
    os.environ.get("GLUU_KV_PORT", 8500),
)

# consul consistency mode
GLUU_CONSUL_CONSISTENCY = os.environ.get("GLUU_CONSUL_CONSISTENCY", "stale")

GLUU_CONSUL_SCHEME = os.environ.get("GLUU_CONSUL_SCHEME", "http")

GLUU_CONSUL_VERIFY = os.environ.get("GLUU_CONSUL_VERIFY", False)

# abspath to Consul CA cert file
GLUU_CONSUL_CACERT_FILE = os.environ.get("GLUU_CONSUL_CACERT_FILE",
                                         "/etc/certs/consul_ca.crt")

# abspath to Consul cert file
GLUU_CONSUL_CERT_FILE = os.environ.get("GLUU_CONSUL_CERT_FILE",
                                       "/etc/certs/consul_client.crt")

# abspath to Consul key file
GLUU_CONSUL_KEY_FILE = os.environ.get("GLUU_CONSUL_KEY_FILE",
                                      "/etc/certs/consul_client.key")

# abspath to Consul token file
GLUU_CONSUL_TOKEN_FILE = os.environ.get("GLUU_CONSUL_TOKEN_FILE",
                                        "/etc/certs/consul_token")

# the namespace used for storing configmap
GLUU_KUBERNETES_NAMESPACE = os.environ.get("GLUU_KUBERNETES_NAMESPACE",
                                           "default")
# the name of the configmap
GLUU_KUBERNETES_CONFIGMAP = os.environ.get("GLUU_KUBERNETES_CONFIGMAP", "gluu")


def as_boolean(val, default=False):
    truthy = set(('t', 'T', 'true', 'True', 'TRUE', '1', 1, True))
    falsy = set(('f', 'F', 'false', 'False', 'FALSE', '0', 0, False))

    if val in truthy:
        return True
    if val in falsy:
        return False
    return default


class BaseConfig(object):
    """Base class for config storage. Must be sub-classed per
    implementation details.
    """

    def get(self, key, default=None):
        """Get specific config.

        Subclass __MUST__ implement this method.
        """
        raise NotImplementedError

    def set(self, key, value):
        """Set specific config.

        Subclass __MUST__ implement this method.
        """
        raise NotImplementedError

    def all(self):
        """Get all config as ``dict`` type.

        Subclass __MUST__ implement this method.
        """
        raise NotImplementedError

    def _prepare_value(self, value):
        if not isinstance(value, (six.string_types, six.binary_type)):
            value = json.dumps(value)
        return value


class ConsulConfig(BaseConfig):
    def __init__(self):
        self.prefix = "gluu/config/"

        token = None
        if os.path.isfile(GLUU_CONSUL_TOKEN_FILE):
            with open(GLUU_CONSUL_TOKEN_FILE) as fr:
                token = fr.read().strip()

        cert = None
        if all([os.path.isfile(GLUU_CONSUL_CERT_FILE),
                os.path.isfile(GLUU_CONSUL_KEY_FILE)]):
            cert = (GLUU_CONSUL_CERT_FILE, GLUU_CONSUL_KEY_FILE)

        verify = as_boolean(GLUU_CONSUL_VERIFY)
        # verify using CA cert
        if os.path.isfile(GLUU_CONSUL_CACERT_FILE):
            verify = GLUU_CONSUL_CACERT_FILE

        self._request_warning(GLUU_CONSUL_SCHEME, verify)

        self.client = Consul(
            host=GLUU_CONSUL_HOST,
            port=GLUU_CONSUL_PORT,
            token=token,
            scheme=GLUU_CONSUL_SCHEME,
            consistency=GLUU_CONSUL_CONSISTENCY,
            verify=verify,
            cert=cert,
        )

    def _merge_path(self, key):
        """Add prefix to the key.
        """
        return "".join([self.prefix, key])

    def _unmerge_path(self, key):
        """Remove prefix from the key.
        """
        return key[len(self.prefix):]

    def get(self, key, default=None):
        _, result = self.client.kv.get(self._merge_path(key))
        if not result:
            return default
        return result["Value"]

    def set(self, key, value):
        return self.client.kv.put(self._merge_path(key),
                                  self._prepare_value(value))

    def find(self, key):
        _, resultset = self.client.kv.get(self._merge_path(key),
                                          recurse=True)

        if not resultset:
            return {}

        return {
            self._unmerge_path(item["Key"]): item["Value"]
            for item in resultset
        }

    def all(self):
        return self.find("")

    def _request_warning(self, scheme, verify):
        if scheme == "https" and verify is False:
            import urllib3
            urllib3.disable_warnings()
            logger.warn("All requests to Consul will be unverified. "
                        "Please adjust GLUU_CONSUL_SCHEME and "
                        "GLUU_CONSUL_VERIFY environment variables.")


class KubernetesConfig(BaseConfig):
    def __init__(self):
        kubernetes.config.load_incluster_config()
        self.client = kubernetes.client.CoreV1Api()
        self.name_exists = False

    def get(self, key, default=None):
        result = self.all()
        return result.get(key, default)

    def _prepare_configmap(self):
        # create a configmap name if not exist
        if not self.name_exists:
            try:
                self.client.read_namespaced_config_map(
                    GLUU_KUBERNETES_CONFIGMAP,
                    GLUU_KUBERNETES_NAMESPACE)
                self.name_exists = True
            except kubernetes.client.rest.ApiException as exc:
                if exc.status == 404:
                    # create the configmaps name
                    body = {
                        "kind": "ConfigMap",
                        "apiVersion": "v1",
                        "metadata": {
                            "name": GLUU_KUBERNETES_CONFIGMAP,
                        },
                        "data": {},
                    }
                    created = self.client.create_namespaced_config_map(
                        GLUU_KUBERNETES_NAMESPACE,
                        body)
                    if created:
                        self.name_exists = True
                else:
                    raise

    def set(self, key, value):
        self._prepare_configmap()
        body = {
            "kind": "ConfigMap",
            "apiVersion": "v1",
            "metadata": {
                "name": GLUU_KUBERNETES_CONFIGMAP,
            },
            "data": {
                key: self._prepare_value(value),
            }
        }
        return self.client.patch_namespaced_config_map(
            GLUU_KUBERNETES_CONFIGMAP,
            GLUU_KUBERNETES_NAMESPACE,
            body=body)

    def all(self):
        self._prepare_configmap()
        result = self.client.read_namespaced_config_map(
            GLUU_KUBERNETES_CONFIGMAP,
            GLUU_KUBERNETES_NAMESPACE)
        return result.data or {}


class ConfigManager(object):
    def __init__(self):
        if GLUU_CONFIG_ADAPTER == "consul":
            self.adapter = ConsulConfig()
        elif GLUU_CONFIG_ADAPTER == "kubernetes":
            self.adapter = KubernetesConfig()
        else:
            self.adapter = None

    def get(self, key, default=None):
        return self.adapter.get(key, default)

    def set(self, key, value):
        return self.adapter.set(key, value)

    def all(self):
        return self.adapter.all()

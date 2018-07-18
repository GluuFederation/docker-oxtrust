import json
import os

import six
import kubernetes.client
import kubernetes.config
from consul import Consul

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

# the namespace used for storing configmap
GLUU_KUBERNETES_NAMESPACE = os.environ.get("GLUU_KUBERNETES_NAMESPACE", "default")
# the name of the configmap
GLUU_KUBERNETES_CONFIGMAP = os.environ.get("GLUU_KUBERNETES_CONFIGMAP", "gluu")


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
        self.client = Consul(host=GLUU_CONSUL_HOST,
                             port=GLUU_CONSUL_PORT,
                             consistency=GLUU_CONSUL_CONSISTENCY)

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
        return {
            self._unmerge_path(item["Key"]): item["Value"]
            for item in resultset
        }

    def all(self):
        return self.find("")


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

    # def find(self, key):
    #     return self.adapter.find(key)

    def all(self):
        return self.adapter.all()

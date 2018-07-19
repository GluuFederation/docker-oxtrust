# oxTrust

A docker image version of oxTrust.

## Latest Stable Release

The latest stable release is `gluufederation/oxtrust:3.1.3_02`. Click [here](./CHANGES.md) for archived versions.

## Versioning/Tagging

This image uses its own versioning/tagging format.

    <IMAGE-NAME>:<GLUU-SERVER-VERSION>_<RELEASE_VERSION>

For example, `gluufederation/oxtrust:3.1.3_02` consists of:

- `gluufederation/oxtrust` as `<IMAGE_NAME>`: the actual image name
- `3.1.3` as `GLUU-SERVER-VERSION`: the Gluu Server version as setup reference
- `02` as `<RELEASE_VERSION>`

## Installation

Pull the image:

    docker pull gluufederation/oxtrust:3.1.3_02

## Environment Variables

- `GLUU_LDAP_URL`: URL to LDAP in `host:port` format string (i.e. `192.168.100.4:1636`); multiple URLs can be used using comma-separated value (i.e. `192.168.100.1:1636,192.168.100.2:1636`).
- `GLUU_CUSTOM_OXTRUST_URL`: URL to downloadable custom oxTrust files packed using `.tar.gz` format.
- `GLUU_OXAUTH_BACKEND`: the address of oxAuth backend, default to `localhost:8081`
- `GLUU_SHIB_SOURCE_DIR`: absolute path to directory to copy Shibboleth config from (default to `/opt/shibboleth-idp`)
- `GLUU_SHIB_TARGET_DIR`: absolute path to directory to copy Shibboleth config to (default to `/opt/shared-shibboleth-idp`)
- `GLUU_CONFIG_ADAPTER`: config backend (either `consul` for Consul KV or `kubernetes` for Kubernetes configmap)

The following environment variables are activated only if `GLUU_CONFIG_ADAPTER` is set to `consul`:

- `GLUU_CONSUL_HOST`: hostname or IP of Consul (default to `localhost`)
- `GLUU_CONSUL_PORT`: port of Consul (default to `8500`)
- `GLUU_CONSUL_CONSISTENCY`: Consul consistency mode (choose one of `default`, `consistent`, or `stale`). Default to `stale` mode.

otherwise, if `GLUU_CONFIG_ADAPTER` is set to `kubernetes`:

- `GLUU_KUBERNETES_NAMESPACE`: Kubernetes namespace (default to `default`)
- `GLUU_KUBERNETES_CONFIGMAP`: Kubernetes configmap name (default to `gluu`)

## Volumes

1. `/opt/gluu/jetty/identity/custom/pages` directory
2. `/opt/gluu/jetty/identity/custom/static` directory
3. `/opt/gluu/jetty/identity/lib/ext` directory

## Running The Container

Here's an example to run the container:

```
docker run -d \
    --name oxtrust \
    -e GLUU_CONSUL_HOST=consul.example.com \
    -e GLUU_LDAP_URL=ldap.example.com:1636 \
    -v $PWD/shared-shibboleth-idp:/opt/shared-shibboleth-idp \
    gluufederation/oxtrust:3.1.3_02
```

*NOTE*: the use of `-v $PWD/shared-shibboleth-idp:/opt/shared-shibboleth-idp` is required if we want to add oxShibboleth container.
See [oxShibboleth's Design Decisions](https://github.com/GluuFederation/docker-oxshibboleth/tree/3.1.3#design-decisions) section for details.

## Customizing oxTrust

oxTrust can be customized by providing HTML pages, static resource files (i.e. CSS), or JAR libraries.
Refer to https://gluu.org/docs/ce/3.1.3/operation/custom-design/ for an example on how to customize oxTrust.

There are 2 ways to run oxTrust with custom files:

1.  Pass `GLUU_CUSTOM_OXTRUST_URL` environment variable; the container will download and extract the file into
    appropriate location before running the application.

    ```
    docker run -d \
        --name oxtrust \
        -e GLUU_CONSUL_HOST=consul.example.com \
        -e GLUU_LDAP_URL=ldap.example.com:1636 \
        -e GLUU_CUSTOM_OXTRUST_URL=http://files.example.com/resources/custom-oxtrust.tar.gz \
        -v $PWD/shared-shibboleth-idp:/opt/shared-shibboleth-idp \
        gluufederation/oxtrust:3.1.3_02
    ```

    The `.tar.gz` file must consist of following directories:

    ```
    ├── lib
    │   └── ext
    ├── pages
    └── static
    ```

2.  Map volumes from host to container.

    ```
    docker run -d \
        --name oxtrust \
        -e GLUU_CONSUL_HOST=consul.example.com \
        -e GLUU_LDAP_URL=ldap.example.com:1636 \
        -v $PWD/custom/pages:/opt/gluu/jetty/identity/custom/pages \
        -v $PWD/custom/static:/opt/gluu/jetty/identity/custom/static \
        -v $PWD/custom/lib/ext:/opt/gluu/jetty/identity/lib/ext \
        -v $PWD/shared-shibboleth-idp:/opt/shared-shibboleth-idp \
        gluufederation/oxtrust:3.1.3_02
    ```

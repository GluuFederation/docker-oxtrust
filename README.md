# oxTrust

A docker image version of oxTrust.

## Environment Variables

- `GLUU_KV_HOST`: hostname or IP address of Consul.
- `GLUU_KV_PORT`: port of Consul.
- `GLUU_LDAP_URL`: URL to LDAP in `host:port` format string (i.e. `192.168.100.4:1636`); multiple URLs can be used using comma-separated value (i.e. `192.168.100.1:1636,192.168.100.2:1636`).
- `GLUU_CUSTOM_OXTRUST_URL`: URL to downloadable custom oxTrust files packed using `.tar.gz` format.

## Volumes

1. `/opt/gluu/jetty/identity/custom/pages` directory
2. `/opt/gluu/jetty/identity/custom/static` directory
3. `/opt/gluu/jetty/identity/lib/ext` directory

## Running The Container

Here's an example to run the container:

```
docker run -d \
    --name oxtrust \
    -e GLUU_KV_HOST=consul.example.com \
    -e GLUU_KV_PORT=8500 \
    -e GLUU_LDAP_URL=ldap.example.com:1636 \
    -v $PWD/shared-shibboleth-idp:/opt/shared-shibboleth-idp \
    gluufederation/oxtrust:3.1.2_dev
```

*NOTE*: the use of `-v $PWD/shared-shibboleth-idp:/opt/shared-shibboleth-idp` is required if we want to add oxShibboleth container.
See [oxShibboleth's Design Decisions](https://github.com/GluuFederation/docker-oxshibboleth/tree/3.1.2#design-decisions) section for details.

## Customizing oxTrust

oxTrust can be customized by providing HTML pages, static resource files (i.e. CSS), or JAR libraries.
Refer to https://gluu.org/docs/ce/3.1.2/operation/custom-design/ for an example on how to customize oxTrust.

There are 2 ways to run oxTrust with custom files:

1.  Pass `GLUU_CUSTOM_OXTRUST_URL` environment variable; the container will download and extract the file into
    appropriate location before running the application.

    ```
    docker run -d \
        --name oxtrust \
        -e GLUU_KV_HOST=consul.example.com \
        -e GLUU_KV_PORT=8500 \
        -e GLUU_LDAP_URL=ldap.example.com:1636 \
        -e GLUU_CUSTOM_OXTRUST_URL=http://files.example.com/resources/custom-oxtrust.tar.gz \
        -v $PWD/shared-shibboleth-idp:/opt/shared-shibboleth-idp \
        gluufederation/oxtrust:3.1.2_dev
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
        -e GLUU_KV_HOST=consul.example.com \
        -e GLUU_KV_PORT=8500 \
        -e GLUU_LDAP_URL=ldap.example.com:1636 \
        -v $PWD/custom/pages:/opt/gluu/jetty/identity/custom/pages \
        -v $PWD/custom/static:/opt/gluu/jetty/identity/custom/static \
        -v $PWD/custom/lib/ext:/opt/gluu/jetty/identity/lib/ext \
        -v $PWD/shared-shibboleth-idp:/opt/shared-shibboleth-idp \
        gluufederation/identity:3.1.2_dev
    ```

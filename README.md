# oxTrust

A docker image version of oxTrust.

## Latest Stable Release

Latest stable release is `gluufederation/oxtrust:3.0.1_rev1.0.0-beta2`. See `CHANGES.md` for archives.

## Versioning/Tagging

This image uses its own versioning/tagging format.

    <IMAGE-NAME>:<GLUU-SERVER-VERSION>_<INTERNAL-REV-VERSION>

For example, `gluufederation/oxtrust:3.0.1_rev1.0.0` consists of:

- glufederation/oxtrust as `<IMAGE_NAME>`; the actual image name
- 3.0.1 as `GLUU-SERVER-VERSION`; the Gluu Server version as setup reference
- rev1.0.0 as `<INTERNAL-REV-VERSION>`; revision made when developing the image

## Installation

Build the image:

```
docker build --rm --force-rm -t gluufederation/oxtrust:latest .
```

Or get it from Docker Hub:

```
docker pull gluufederation/oxtrust:latest
```

## Environment Variables

- `GLUU_KV_HOST`: hostname or IP address of Consul.
- `GLUU_KV_PORT`: port of Consul.
- `GLUU_LDAP_URL`: URL to LDAP (single URL or comma-separated URLs).
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
    -e GLUU_KV_HOST=my.consul.domain.com \
    -e GLUU_KV_PORT=8500 \
    -e GLUU_LDAP_URL=my.ldap.domain.com:1636 \
    -e GLUU_CUSTOM_OXTRUST_URL=http://my.domain.com/resource/custom-oxtrust.tar.gz \
    gluufederation/oxtrust:containership
```

## Customizing oxTrust

oxTrust can be customized by providing HTML pages, static resource files (i.e. CSS), or JAR libraries.
Refer to https://gluu.org/docs/ce/3.0.1/operation/custom-loginpage/ for an example on how to customize oxTrust.

There are 2 ways to run oxTrust with custom files:

1.  Pass `GLUU_CUSTOM_OXTRUST_URL` environment variable; the container will download and extract the file into
    appropriate location before running the application.

    ```
    docker run -d \
        --name oxtrust \
        -e GLUU_KV_HOST=my.consul.domain.com \
        -e GLUU_KV_PORT=8500 \
        -e GLUU_LDAP_URL=my.ldap.domain.com:1636 \
        -e GLUU_CUSTOM_OXTRUST_URL=http://my.domain.com/resources/custom-oxtrust.tar.gz \
        gluufederation/oxtrust:containership
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
        -e GLUU_KV_HOST=my.consul.domain.com \
        -e GLUU_KV_PORT=8500 \
        -e GLUU_LDAP_URL=my.ldap.domain.com:1636 \
        -v /path/to/custom/pages:/opt/gluu/jetty/identity/custom/pages \
        -v /path/to/custom/static:/opt/gluu/jetty/identity/custom/static \
        -v /path/to/custom/lib/ext:/opt/gluu/jetty/identity/lib/ext \
        gluufederation/identity:containership
    ```

#!/bin/sh
set -e

import_ssl_cert() {
    if [ -f /etc/certs/gluu_https.crt ]; then
        openssl x509 -outform der -in /etc/certs/gluu_https.crt -out /etc/certs/gluu_https.der
        keytool -importcert -trustcacerts \
            -alias gluu_https \
            -file /etc/certs/gluu_https.der \
            -keystore /usr/lib/jvm/default-jvm/jre/lib/security/cacerts \
            -storepass changeit \
            -noprompt
    fi
}

download_custom_tar() {
    if [ ! -z ${GLUU_CUSTOM_OXTRUST_URL} ]; then
        mkdir -p /tmp/identity
        wget -q ${GLUU_CUSTOM_OXTRUST_URL} -O /tmp/identity/custom-identity.tar.gz
        cd /tmp/identity
        tar xf custom-identity.tar.gz

        if [ -d /tmp/identity/pages ]; then
            cp -R /tmp/identity/pages/ /opt/gluu/jetty/identity/custom/
        fi

        if [ -d /tmp/identity/static ]; then
            cp -R /tmp/identity/static/ /opt/gluu/jetty/identity/custom/
        fi

        if [ -d /tmp/identity/i18n ]; then
            cp -R /tmp/identity/i18n/ /opt/gluu/jetty/identity/custom/
        fi

        if [ -d /tmp/identity/libs ]; then
            cp -R /tmp/identity/libs/ /opt/gluu/jetty/identity/custom/
        fi

        if [ -d /tmp/identity/lib/ext ]; then
            cp -R /tmp/identity/lib/ext/ /opt/gluu/jetty/identity/lib/
        fi
    fi
}

pull_shared_shib_files() {
    # sync with existing files in target directory (mapped volume)
    mkdir -p "$GLUU_SHIB_TARGET_DIR" "$GLUU_SHIB_SOURCE_DIR"
    if [ -n "$(ls -A $GLUU_SHIB_TARGET_DIR 2>/dev/null)" ]; then
        cp -r $GLUU_SHIB_TARGET_DIR/* $GLUU_SHIB_SOURCE_DIR
    fi
}

if [ ! -f /touched ]; then
    download_custom_tar
    if [ -f /etc/redhat-release ]; then
        source scl_source enable python27 && python /opt/scripts/entrypoint.py
    else
        python /opt/scripts/entrypoint.py
    fi
    import_ssl_cert
    pull_shared_shib_files
    touch /touched
fi

# monitor filesystem changes on Shibboleth-related files
sh /opt/scripts/shibwatcher.sh &

get_java_opts() {
    local java_opts="
        -server \
        -Xms256m \
        -Xmx2048m \
        -XX:+UnlockExperimentalVMOptions \
        -XX:+UseCGroupMemoryLimitForHeap \
        -XX:MaxRAMFraction=$GLUU_MAX_RAM_FRACTION \
        -XX:+DisableExplicitGC \
        -Dgluu.base=/etc/gluu \
        -Dserver.base=/opt/gluu/jetty/identity \
        -Dlog.base=/opt/gluu/jetty/identity \
        -Dorg.eclipse.jetty.server.Request.maxFormContentSize=50000000 \
        -Dpython.home=/opt/jython

    "

    if [ -n "${GLUU_DEBUG_PORT}" ]; then
        java_opts="
            ${java_opts}
            -agentlib:jdwp=transport=dt_socket,address=${GLUU_DEBUG_PORT},server=y,suspend=n
        "
    fi

    echo "${java_opts}"
}

cd /opt/gluu/jetty/identity
exec java \
     $(get_java_opts) \
     -jar /opt/jetty/start.jar

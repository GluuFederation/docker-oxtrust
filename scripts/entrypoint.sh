#!/bin/sh
set -e

cat << LICENSE_ACK

# ========================================================================================= #
# Gluu License Agreement: https://github.com/GluuFederation/gluu-docker/blob/4.0.0/LICENSE. #
# The use of Gluu Server Docker Edition is subject to the Gluu Support License.             #
# ========================================================================================= #

LICENSE_ACK

import_ssl_cert() {
    if [ -f /etc/certs/gluu_https.crt ]; then
        openssl x509 -outform der -in /etc/certs/gluu_https.crt -out /etc/certs/gluu_https.der
        keytool -importcert -trustcacerts \
            -alias gluu_https \
            -file /etc/certs/gluu_https.der \
            -keystore /usr/lib/jvm/default-jvm/jre/lib/security/cacerts \
            -storepass changeit \
            -noprompt

        # satisfy oxTrust
        ln -s /etc/certs/gluu_https.crt /etc/certs/httpd.crt
    fi
}

pull_shared_shib_files() {
    # sync with existing files in target directory (mapped volume)
    mkdir -p "$GLUU_SHIB_TARGET_DIR" "$GLUU_SHIB_SOURCE_DIR"
    if [ -n "$(ls -A $GLUU_SHIB_TARGET_DIR 2>/dev/null)" ]; then
        cp -r $GLUU_SHIB_TARGET_DIR/* $GLUU_SHIB_SOURCE_DIR
    fi
}

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

if [ -f /etc/redhat-release ]; then
    source scl_source enable python27 && python /opt/scripts/wait_for.py --deps="config,secret,ldap,oxauth"
else
    python /opt/scripts/wait_for.py --deps="config,secret,ldap,oxauth"
fi

if [ ! -f /deploy/touched ]; then
    if [ -f /touched ]; then
        # backward-compat
        mv /touched /deploy/touched
    else
        if [ -f /etc/redhat-release ]; then
            source scl_source enable python27 && python /opt/scripts/entrypoint.py
        else
            python /opt/scripts/entrypoint.py
        fi

        import_ssl_cert
        pull_shared_shib_files
        touch /deploy/touched
    fi
fi

# monitor filesystem changes on Shibboleth-related files
sh /opt/scripts/shibwatcher.sh &

cd /opt/gluu/jetty/identity
exec java \
     $(get_java_opts) \
     -jar /opt/jetty/start.jar

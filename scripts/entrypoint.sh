#!/bin/sh
set -e

# =========
# FUNCTIONS
# =========

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

# ==========
# ENTRYPOINT
# ==========

cat << LICENSE_ACK

# ========================================================================================= #
# Gluu License Agreement: https://github.com/GluuFederation/gluu-docker/blob/4.0.0/LICENSE. #
# The use of Gluu Server Docker Edition is subject to the Gluu Support License.             #
# ========================================================================================= #

LICENSE_ACK

# check persistence type
case "${GLUU_PERSISTENCE_TYPE}" in
    ldap|couchbase|hybrid)
        ;;
    *)
        echo "unsupported GLUU_PERSISTENCE_TYPE value; please choose 'ldap', 'couchbase', or 'hybrid'"
        exit 1
        ;;
esac

# check mapping used by LDAP
if [ "${GLUU_PERSISTENCE_TYPE}" = "hybrid" ]; then
    case "${GLUU_PERSISTENCE_LDAP_MAPPING}" in
        default|user|cache|site|statistic)
            ;;
        *)
            echo "unsupported GLUU_PERSISTENCE_LDAP_MAPPING value; please choose 'default', 'user', 'cache', 'site', or 'statistic'"
            exit 1
            ;;
    esac
fi

# run wait_for functions
deps="config,secret"

if [ "${GLUU_PERSISTENCE_TYPE}" = "hybrid" ]; then
    deps="${deps},ldap,couchbase"
else
    deps="${deps},${GLUU_PERSISTENCE_TYPE}"
fi

deps="$deps,oxauth"

if [ -f /etc/redhat-release ]; then
    source scl_source enable python27 && gluu-wait --deps="${deps}"
else
    gluu-wait --deps="${deps}"
fi

if [ ! -f /deploy/touched ]; then
    if [ -f /touched ]; then
        # backward-compat
        mv /touched /deploy/touched
    else
        if [ -f /etc/redhat-release ]; then
            source scl_source enable python27 && python /app/scripts/entrypoint.py
        else
            python /app/scripts/entrypoint.py
        fi

        import_ssl_cert
        pull_shared_shib_files
        touch /deploy/touched
    fi
fi

# monitor filesystem changes on Shibboleth-related files
sh /app/scripts/shibwatcher.sh &

# enable passport menu (a workaround)
mkdir -p /opt/gluu/node/passport/server

cd /opt/gluu/jetty/identity
exec java \
     $(get_java_opts) \
     -jar /opt/jetty/start.jar

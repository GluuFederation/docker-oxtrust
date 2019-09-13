#!/bin/sh
set -e

# =========
# FUNCTIONS
# =========

pull_shared_shib_files() {
    # sync with existing files in target directory (mapped volume)
    mkdir -p "$GLUU_SHIB_TARGET_DIR" "$GLUU_SHIB_SOURCE_DIR"
    if [ -n "$(ls -A $GLUU_SHIB_TARGET_DIR 2>/dev/null)" ]; then
        cp -r $GLUU_SHIB_TARGET_DIR/* $GLUU_SHIB_SOURCE_DIR
    fi
}

get_java_opts() {
    local java_opts="
        -XX:+DisableExplicitGC \
        -XX:+UseContainerSupport \
        -XX:MaxRAMPercentage=$GLUU_MAX_RAM_PERCENTAGE \
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

# ================================================================================================ #
# Gluu License Agreement: https://github.com/GluuFederation/enterprise-edition/blob/4.0.0/LICENSE. #
# The use of Gluu Server Enterprise Edition is subject to the Gluu Support License.                #
# ================================================================================================ #

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
        default|user|cache|site|token)
            ;;
        *)
            echo "unsupported GLUU_PERSISTENCE_LDAP_MAPPING value; please choose 'default', 'user', 'cache', 'site', or 'token'"
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
    if [ -f /etc/redhat-release ]; then
        source scl_source enable python27 && python /app/scripts/entrypoint.py
    else
        python /app/scripts/entrypoint.py
    fi

    pull_shared_shib_files
    touch /deploy/touched
fi

# monitor filesystem changes on Shibboleth-related files
sh /app/scripts/shibwatcher.sh &

# enable passport menu (a workaround for https://git.io/fjQCu)
mkdir -p /opt/gluu/node/passport/server

# enable radius menu (a workaround for https://git.io/fjQCc)
mkdir -p /opt/gluu/radius && echo 'dummy file to enable Radius menu' > /opt/gluu/radius/super-gluu-radius-server.jar

# # enable shib3 menu (a workaround for https://git.io/fjQCW)
# mkdir -p /opt/gluu/jetty/idp/webapps && echo 'dummy file to enable Shibboleth3 menu' > /opt/gluu/jetty/idp/webapps/idp.war

cd /opt/gluu/jetty/identity
exec java \
     $(get_java_opts) \
     -jar /opt/jetty/start.jar -server

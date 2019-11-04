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

get_debug_opt() {
    debug_opt=""
    if [ -n "${GLUU_DEBUG_PORT}" ]; then
        debug_opt="
            -agentlib:jdwp=transport=dt_socket,address=${GLUU_DEBUG_PORT},server=y,suspend=n
        "
    fi

    echo "${debug_opt}"
}

run_wait() {
    python /app/scripts/wait.py
}

run_entrypoint() {
    # move oxtrust-api lib
    if [ ! -f /opt/gluu/jetty/identity/custom/libs/oxtrust-api-server-${GLUU_VERSION}.jar ]; then
        mkdir -p /opt/gluu/jetty/identity/custom/libs
        mv /tmp/oxtrust-api-server-${GLUU_VERSION}.jar /opt/gluu/jetty/identity/custom/libs/oxtrust-api-server-${GLUU_VERSION}.jar
    fi

    if [ ! -f /deploy/touched ]; then
        python /app/scripts/entrypoint.py
        pull_shared_shib_files
        ln -s /etc/certs/gluu_https.crt /etc/certs/httpd.crt
        touch /deploy/touched
    fi
}

# ==========
# ENTRYPOINT
# ==========

cat << LICENSE_ACK

# ================================================================================= #
# Gluu License Agreement: https://www.gluu.org/support-license/                     #
# The use of Gluu Server Enterprise Edition is subject to the Gluu Support License. #
# ================================================================================= #

LICENSE_ACK

if [ -f /etc/redhat-release ]; then
    source scl_source enable python27 && run_wait
    source scl_source enable python27 && run_entrypoint
else
    run_wait
    run_entrypoint
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
mkdir -p /opt/jetty/temp
exec java \
    -server \
    -XX:+DisableExplicitGC \
    -XX:+UseContainerSupport \
    -XX:MaxRAMPercentage=$GLUU_MAX_RAM_PERCENTAGE \
    -Dgluu.base=/etc/gluu \
    -Dserver.base=/opt/gluu/jetty/identity \
    -Dlog.base=/opt/gluu/jetty/identity \
    -Dorg.eclipse.jetty.server.Request.maxFormContentSize=50000000 \
    -Dpython.home=/opt/jython \
    -Djava.io.tmpdir=/opt/jetty/temp \
    $(get_debug_opt) \
    -jar /opt/jetty/start.jar

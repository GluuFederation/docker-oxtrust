#!/bin/sh
set -e

# =========
# FUNCTIONS
# =========

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

move_builtin_jars() {
    # move oxtrust-api lib
    if [ ! -f /opt/gluu/jetty/identity/custom/libs/oxtrust-api-server.jar ]; then
        mkdir -p /opt/gluu/jetty/identity/custom/libs
        mv /tmp/oxtrust-api-server.jar /opt/gluu/jetty/identity/custom/libs/oxtrust-api-server.jar
    fi
}

run_entrypoint() {
    if [ ! -f /deploy/touched ]; then
        python /app/scripts/entrypoint.py
        ln -s /etc/certs/gluu_https.crt /etc/certs/httpd.crt
        touch /deploy/touched
    fi
}

run_jca_sync() {
    python3 /app/scripts/jca_sync.py &
}

run_mod_context() {
    python3 /app/scripts/mod_context.py
}

# ==========
# ENTRYPOINT
# ==========

move_builtin_jars

if [ -f /etc/redhat-release ]; then
    source scl_source enable python27 && run_wait
    source scl_source enable python3 && run_jca_sync
    source scl_source enable python27 && run_entrypoint
    source scl_source enable python27 && run_mod_context
else
    run_wait
    run_jca_sync
    run_entrypoint
    run_mod_context
fi

# enable passport menu (a workaround for https://git.io/fjQCu)
mkdir -p /opt/gluu/node/passport/server

# enable radius menu (a workaround for https://git.io/fjQCc)
mkdir -p /opt/gluu/radius && echo 'dummy file to enable Radius menu' > /opt/gluu/radius/super-gluu-radius-server.jar

# # enable shib3 menu (a workaround for https://git.io/fjQCW)
# mkdir -p /opt/gluu/jetty/idp/webapps && echo 'dummy file to enable Shibboleth3 menu' > /opt/gluu/jetty/idp/webapps/idp.war

# python /app/scripts/shibwatcher.py watch-files &
# python /app/scripts/shibwatcher.py watch-containers &


mkdir -p /opt/jetty/temp
cd /opt/gluu/jetty/identity
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

#!/bin/bash
set -e

import_ssl_cert() {
    if [ -f /etc/certs/gluu_https.crt ]; then
        openssl x509 -outform der -in /etc/certs/gluu_https.crt -out /etc/certs/gluu_https.der
        keytool -importcert -trustcacerts \
            -alias gluu_https \
            -file /etc/certs/gluu_https.der \
            -keystore /usr/lib/jvm/default-java/jre/lib/security/cacerts \
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

        if [ -d /tmp/identity/lib/ext ]; then
            cp -R /tmp/identity/lib/ext/ /opt/gluu/jetty/identity/lib/
        fi
    fi
}



if [ ! -f /touched ]; then
    download_custom_tar
    python /opt/scripts/entrypoint.py
    import_ssl_cert
    touch /touched
fi

cd /opt/gluu/jetty/identity
exec gosu root java -jar /opt/jetty/start.jar -server \
    -Xms256m -Xmx2048m -XX:+DisableExplicitGC \
    -Dgluu.base=/etc/gluu \
    -Dcatalina.base=/opt/gluu/jetty/identity \
    -Dorg.eclipse.jetty.server.Request.maxFormContentSize=50000000 \
    -Dpython.home=/opt/jython

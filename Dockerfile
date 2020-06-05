FROM openjdk:8-jre-alpine3.9

# ===============
# Alpine packages
# ===============

RUN apk update \
    && apk add --no-cache coreutils openssl py-pip ruby py3-pip \
    && apk add --no-cache --virtual build-deps wget git

# =====
# Jetty
# =====

ENV JETTY_VERSION=9.4.24.v20191120 \
    JETTY_HOME=/opt/jetty \
    JETTY_BASE=/opt/gluu/jetty \
    JETTY_USER_HOME_LIB=/home/jetty/lib

# Install jetty
RUN wget -q https://repo1.maven.org/maven2/org/eclipse/jetty/jetty-distribution/${JETTY_VERSION}/jetty-distribution-${JETTY_VERSION}.tar.gz -O /tmp/jetty.tar.gz \
    && mkdir -p /opt \
    && tar -xzf /tmp/jetty.tar.gz -C /opt \
    && mv /opt/jetty-distribution-${JETTY_VERSION} ${JETTY_HOME} \
    && rm -rf /tmp/jetty.tar.gz

# Ports required by jetty
EXPOSE 8080

# ======
# Jython
# ======

ENV JYTHON_VERSION=2.7.2
RUN wget -q https://ox.gluu.org/dist/jython/${JYTHON_VERSION}/jython-installer-${JYTHON_VERSION}.jar -O /tmp/jython-installer.jar \
    && mkdir -p /opt/jython \
    && java -jar /tmp/jython-installer.jar -v -s -d /opt/jython \
    && rm -f /tmp/jython-installer.jar

# =======
# oxTrust
# =======

ENV GLUU_VERSION=4.1.1.Final \
    GLUU_BUILD_DATE="2020-05-26 18:00"

# Install oxTrust
RUN wget -q https://ox.gluu.org/maven/org/gluu/oxtrust-server/${GLUU_VERSION}/oxtrust-server-${GLUU_VERSION}.war -O /tmp/oxtrust.war \
    && mkdir -p ${JETTY_BASE}/identity/webapps/identity \
    && unzip -qq /tmp/oxtrust.war -d ${JETTY_BASE}/identity/webapps/identity \
    && java -jar ${JETTY_HOME}/start.jar jetty.home=${JETTY_HOME} jetty.base=${JETTY_BASE}/identity --add-to-start=server,deploy,annotations,resources,http,http-forwarded,threadpool,jsp,websocket \
    && rm -f /tmp/oxtrust.war

# RUN mkdir -p ${JETTY_BASE}/identity/conf \
#     && unzip -q ${JETTY_BASE}/identity/webapps/identity/WEB-INF/lib/oxtrust-configuration-${GLUU_VERSION}.jar shibboleth3/* -d /opt/gluu/jetty/identity/conf

# ===========
# Custom libs
# ===========

# oxTrust API
RUN wget -q https://ox.gluu.org/maven/org/gluu/oxtrust-api-server/${GLUU_VERSION}/oxtrust-api-server-${GLUU_VERSION}.jar -O /tmp/oxtrust-api-server.jar

# ======
# Facter
# ======

RUN gem install facter -v=2.5.7 --no-ri --no-rdoc

# ====
# Tini
# ====

RUN wget -q https://github.com/krallin/tini/releases/download/v0.18.0/tini-static -O /usr/bin/tini \
    && chmod +x /usr/bin/tini

# ======
# rclone
# ======

ARG RCLONE_VERSION=v1.51.0
RUN wget -q https://github.com/rclone/rclone/releases/download/${RCLONE_VERSION}/rclone-${RCLONE_VERSION}-linux-amd64.zip -O /tmp/rclone.zip \
    && unzip -qq /tmp/rclone.zip -d /tmp \
    && mv /tmp/rclone-${RCLONE_VERSION}-linux-amd64/rclone /usr/bin/ \
    && rm -rf /tmp/rclone-${RCLONE_VERSION}-linux-amd64 /tmp/rclone.zip

# ======
# Python
# ======

COPY requirements.txt /tmp/requirements.txt
RUN pip install -U pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

# =======
# Cleanup
# =======

RUN apk del build-deps \
    && rm -rf /var/cache/apk/*

# =======
# License
# =======

RUN mkdir -p /licenses
COPY LICENSE /licenses/

# ==========
# Config ENV
# ==========

ENV GLUU_CONFIG_ADAPTER=consul \
    GLUU_CONFIG_CONSUL_HOST=localhost \
    GLUU_CONFIG_CONSUL_PORT=8500 \
    GLUU_CONFIG_CONSUL_CONSISTENCY=stale \
    GLUU_CONFIG_CONSUL_SCHEME=http \
    GLUU_CONFIG_CONSUL_VERIFY=false \
    GLUU_CONFIG_CONSUL_CACERT_FILE=/etc/certs/consul_ca.crt \
    GLUU_CONFIG_CONSUL_CERT_FILE=/etc/certs/consul_client.crt \
    GLUU_CONFIG_CONSUL_KEY_FILE=/etc/certs/consul_client.key \
    GLUU_CONFIG_CONSUL_TOKEN_FILE=/etc/certs/consul_token \
    GLUU_CONFIG_KUBERNETES_NAMESPACE=default \
    GLUU_CONFIG_KUBERNETES_CONFIGMAP=gluu \
    GLUU_CONFIG_KUBERNETES_USE_KUBE_CONFIG=false

# ==========
# Secret ENV
# ==========

ENV GLUU_SECRET_ADAPTER=vault \
    GLUU_SECRET_VAULT_SCHEME=http \
    GLUU_SECRET_VAULT_HOST=localhost \
    GLUU_SECRET_VAULT_PORT=8200 \
    GLUU_SECRET_VAULT_VERIFY=false \
    GLUU_SECRET_VAULT_ROLE_ID_FILE=/etc/certs/vault_role_id \
    GLUU_SECRET_VAULT_SECRET_ID_FILE=/etc/certs/vault_secret_id \
    GLUU_SECRET_VAULT_CERT_FILE=/etc/certs/vault_client.crt \
    GLUU_SECRET_VAULT_KEY_FILE=/etc/certs/vault_client.key \
    GLUU_SECRET_VAULT_CACERT_FILE=/etc/certs/vault_ca.crt \
    GLUU_SECRET_KUBERNETES_NAMESPACE=default \
    GLUU_SECRET_KUBERNETES_SECRET=gluu \
    GLUU_SECRET_KUBERNETES_USE_KUBE_CONFIG=false

# ===============
# Persistence ENV
# ===============

ENV GLUU_PERSISTENCE_TYPE=ldap \
    GLUU_PERSISTENCE_LDAP_MAPPING=default \
    GLUU_LDAP_URL=localhost:1636 \
    GLUU_COUCHBASE_URL=localhost \
    GLUU_COUCHBASE_USER=admin \
    GLUU_COUCHBASE_CERT_FILE=/etc/certs/couchbase.crt \
    GLUU_COUCHBASE_PASSWORD_FILE=/etc/gluu/conf/couchbase_password \
    GLUU_COUCHBASE_CONN_TIMEOUT=10000 \
    GLUU_COUCHBASE_CONN_MAX_WAIT=20000 \
    GLUU_COUCHBASE_SCAN_CONSISTENCY=not_bounded

# ===========
# Generic ENV
# ===========

ENV GLUU_MAX_RAM_PERCENTAGE=75.0 \
    GLUU_OXAUTH_BACKEND=localhost:8081 \
    GLUU_WAIT_MAX_TIME=300 \
    GLUU_WAIT_SLEEP_DURATION=10 \
    PYTHON_HOME=/opt/jython \
    GLUU_SYNC_SHIB_MANIFESTS=false \
    GLUU_SHIBWATCHER_INTERVAL=10 \
    GLUU_DOCUMENT_STORE_TYPE=LOCAL \
    GLUU_JCA_URL=http://localhost:8080 \
    GLUU_JCA_PASSWORD_FILE=/etc/gluu/conf/jca_password \
    GLUU_JCA_USERNAME=admin

# ==========
# misc stuff
# ==========

LABEL name="oxTrust" \
    maintainer="Gluu Inc. <support@gluu.org>" \
    vendor="Gluu Federation" \
    version="4.1.1" \
    release="04" \
    summary="Gluu oxTrust" \
    description="Gluu Server UI for managing authentication, authorization and users"

RUN mkdir -p /etc/certs \
    /deploy \
    /opt/shibboleth-idp \
    /etc/gluu/conf/shibboleth3 \
    /var/gluu/photos \
    /var/gluu/identity/removed \
    /var/gluu/identity/cr-snapshots \
    ${JETTY_BASE}/identity/custom/pages \
    ${JETTY_BASE}/identity/custom/static \
    ${JETTY_BASE}/identity/custom/i18n \
    ${JETTY_BASE}/identity/custom/libs \
    ${JETTY_BASE}/identity/conf/shibboleth3/idp \
    ${JETTY_BASE}/identity/conf/shibboleth3/sp \
    /app/scripts \
    /app/templates

# Copy templates
COPY jetty/identity_web_resources.xml ${JETTY_BASE}/identity/webapps/
COPY jetty/identity.xml ${JETTY_BASE}/identity/webapps/
# COPY jetty/idp-metadata.xml ${JETTY_BASE}/identity/conf/shibboleth3/idp/idp-metadata.xml
COPY conf/oxTrustLogRotationConfiguration.xml /etc/gluu/conf/
COPY conf/*.tmpl /app/templates/
COPY scripts /app/scripts
RUN chmod +x /app/scripts/entrypoint.sh

# # create jetty user
# RUN useradd -ms /bin/sh --uid 1000 jetty \
#     && usermod -a -G root jetty

# # adjust ownership
# RUN chown -R 1000:1000 /opt/gluu/jetty \
#     && chown -R 1000:1000 /deploy \
#     && chown -R 1000:1000 /opt/shibboleth-idp \
#     && chown -R 1000:1000 /var/ox \
#     && chmod -R g+w /usr/lib/jvm/default-jvm/jre/lib/security/cacerts \
#     && chgrp -R 0 /opt/gluu/jetty && chmod -R g=u /opt/gluu/jetty \
#     && chgrp -R 0 /opt/shibboleth-idp && chmod -R g=u /opt/shibboleth-idp \
#     && chgrp -R 0 /etc/certs && chmod -R g=u /etc/certs \
#     && chgrp -R 0 /etc/gluu && chmod -R g=u /etc/gluu \
#     && chgrp -R 0 /deploy && chmod -R g=u /deploy \
#     && chgrp -R 0 /var/ox && chmod -R g=u /var/ox

# # run as non-root user
# USER 1000

ENTRYPOINT ["tini", "-e", "143", "-g", "--"]
CMD ["sh", "/app/scripts/entrypoint.sh"]

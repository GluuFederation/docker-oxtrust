FROM adoptopenjdk/openjdk11:jre-11.0.8_10-alpine

# symlink JVM
RUN mkdir -p /usr/lib/jvm/default-jvm /usr/java/latest \
    && ln -sf /opt/java/openjdk /usr/lib/jvm/default-jvm/jre \
    && ln -sf /usr/lib/jvm/default-jvm/jre /usr/java/latest/jre

# ===============
# Alpine packages
# ===============

RUN apk update \
    && apk add --no-cache openssl py3-pip tini curl bash \
    && apk add --no-cache --virtual build-deps wget git gcc musl-dev python3-dev libffi-dev openssl-dev libxml2-dev libxslt-dev

# =====
# Jetty
# =====

ARG JETTY_VERSION=9.4.35.v20201120
ARG JETTY_HOME=/opt/jetty
ARG JETTY_BASE=/opt/gluu/jetty
ARG JETTY_USER_HOME_LIB=/home/jetty/lib

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

ARG JYTHON_VERSION=2.7.2
RUN wget -q https://repo1.maven.org/maven2/org/python/jython-installer/${JYTHON_VERSION}/jython-installer-${JYTHON_VERSION}.jar -O /tmp/jython-installer.jar \
    && mkdir -p /opt/jython \
    && java -jar /tmp/jython-installer.jar -v -s -d /opt/jython \
    && rm -f /tmp/jython-installer.jar /tmp/*.properties

# =======
# oxTrust
# =======

ENV GLUU_VERSION=4.2.3.Final
ENV GLUU_BUILD_DATE="2021-02-02 12:42"

# Install oxTrust
RUN wget -q https://ox.gluu.org/maven/org/gluu/oxtrust-server/${GLUU_VERSION}/oxtrust-server-${GLUU_VERSION}.war -O /tmp/oxtrust.war \
    && mkdir -p ${JETTY_BASE}/identity/webapps/identity \
    && unzip -qq /tmp/oxtrust.war -d ${JETTY_BASE}/identity/webapps/identity \
    && java -jar ${JETTY_HOME}/start.jar jetty.home=${JETTY_HOME} jetty.base=${JETTY_BASE}/identity --add-to-start=server,deploy,annotations,resources,http,http-forwarded,threadpool,jsp,websocket \
    && rm -f /tmp/oxtrust.war

# ===========
# Custom libs
# ===========

RUN mkdir -p /usr/share/java

# oxTrust API
RUN wget -q https://ox.gluu.org/maven/org/gluu/oxtrust-api-server/${GLUU_VERSION}/oxtrust-api-server-${GLUU_VERSION}.jar -O /usr/share/java/oxtrust-api-server.jar

# ======
# Facter
# ======

ARG PYFACTER_VERSION=9d8478ee47dc5498a766e010e8d3a3451b46e541
RUN wget -q https://github.com/GluuFederation/gluu-snap/raw/${PYFACTER_VERSION}/facter/facter -O /usr/bin/facter \
    && chmod +x /usr/bin/facter

# ======
# Python
# ======

COPY requirements.txt /app/requirements.txt
RUN pip3 install -U pip \
    && pip3 install --no-cache-dir -r /app/requirements.txt \
    && rm -rf /src/pygluu-containerlib/.git

# =======
# Cleanup
# =======

# webdavclient3 requires binary compiled from libxslt-dev
RUN cp /usr/lib/libxslt.so.1 /tmp/libxslt.so.1 \
    && cp /usr/lib/libexslt.so.0 /tmp/libexslt.so.0 \
    && cp /usr/lib/libxml2.so.2 /tmp/libxml2.so.2 \
    && cp /usr/lib/libgcrypt.so.20 /tmp/libgcrypt.so.20 \
    && cp /usr/lib/libgpg-error.so.0 /tmp/libgpg-error.so.0 \
    && apk del build-deps \
    && rm -rf /var/cache/apk/* \
    && mv /tmp/libxslt.so.1 /usr/lib/libxslt.so.1 \
    && mv /tmp/libexslt.so.0 /usr/lib/libexslt.so.0 \
    && mv /tmp/libxml2.so.2 /usr/lib/libxml2.so.2 \
    && mv /tmp/libgcrypt.so.20 /usr/lib/libgcrypt.so.20 \
    && mv /tmp/libgpg-error.so.0 /usr/lib/libgpg-error.so.0

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
    GLUU_COUCHBASE_SCAN_CONSISTENCY=not_bounded \
    GLUU_COUCHBASE_BUCKET_PREFIX=gluu \
    GLUU_COUCHBASE_TRUSTSTORE_ENABLE=true

# ===========
# Generic ENV
# ===========

ENV GLUU_MAX_RAM_PERCENTAGE=75.0 \
    GLUU_OXAUTH_BACKEND=localhost:8081 \
    GLUU_WAIT_MAX_TIME=300 \
    GLUU_WAIT_SLEEP_DURATION=10 \
    PYTHON_HOME=/opt/jython \
    GLUU_DOCUMENT_STORE_TYPE=LOCAL \
    GLUU_JACKRABBIT_URL=http://localhost:8080 \
    GLUU_JACKRABBIT_ADMIN_ID=admin \
    GLUU_JACKRABBIT_ADMIN_PASSWORD_FILE=/etc/gluu/conf/jackrabbit_admin_password \
    GLUU_JAVA_OPTIONS="" \
    GLUU_SSL_CERT_FROM_SECRETS=false

# ==========
# misc stuff
# ==========

LABEL name="oxTrust" \
    maintainer="Gluu Inc. <support@gluu.org>" \
    vendor="Gluu Federation" \
    version="4.2.3" \
    release="01" \
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
COPY conf/oxTrustLogRotationConfiguration.xml /etc/gluu/conf/
COPY conf/*.tmpl /app/templates/
COPY scripts /app/scripts
RUN chmod +x /app/scripts/entrypoint.sh

ENTRYPOINT ["tini", "-e", "143", "-g", "--"]
CMD ["sh", "/app/scripts/entrypoint.sh"]

FROM openjdk:8-jre-alpine

LABEL maintainer="Gluu Inc. <support@gluu.org>"

# ===============
# Alpine packages
# ===============

RUN apk update && apk add --no-cache \
    coreutils \
    inotify-tools \
    openssl \
    py-pip \
    ruby \
    wget

# =====
# Jetty
# =====

ENV JETTY_VERSION 9.4.9.v20180320
ENV JETTY_TGZ_URL https://repo1.maven.org/maven2/org/eclipse/jetty/jetty-distribution/${JETTY_VERSION}/jetty-distribution-${JETTY_VERSION}.tar.gz
ENV JETTY_HOME /opt/jetty
ENV JETTY_BASE /opt/gluu/jetty
ENV JETTY_USER_HOME_LIB /home/jetty/lib

# Install jetty
RUN wget -q ${JETTY_TGZ_URL} -O /tmp/jetty.tar.gz \
    && mkdir -p /opt \
    && tar -xzf /tmp/jetty.tar.gz -C /opt \
    && mv /opt/jetty-distribution-${JETTY_VERSION} ${JETTY_HOME} \
    && rm -rf /tmp/jetty.tar.gz \
    && mv ${JETTY_HOME}/etc/webdefault.xml ${JETTY_HOME}/etc/webdefault.xml.bak \
    && mv ${JETTY_HOME}/etc/jetty.xml ${JETTY_HOME}/etc/jetty.xml.bak

COPY jetty/webdefault.xml ${JETTY_HOME}/etc/
COPY jetty/jetty.xml ${JETTY_HOME}/etc/

# Ports required by jetty
EXPOSE 8080

# ======
# Jython
# ======

ENV JYTHON_VERSION 2.7.2a1
ENV JYTHON_DOWNLOAD_URL https://ox.gluu.org/dist/jython/${JYTHON_VERSION}/jython-installer.jar
RUN wget -q ${JYTHON_DOWNLOAD_URL} -O /tmp/jython-installer.jar \
    && mkdir -p /opt/jython \
    && java -jar /tmp/jython-installer.jar -v -s -d /opt/jython -t standard -e ensurepip \
    && rm -f /tmp/jython-installer.jar

# =======
# oxTrust
# =======

ENV OX_VERSION 3.1.4.Final
ENV OX_BUILD_DATE 2018-09-28
ENV OXTRUST_DOWNLOAD_URL https://ox.gluu.org/maven/org/xdi/oxtrust-server/${OX_VERSION}/oxtrust-server-${OX_VERSION}.war

# the LABEL defined before downloading ox war/jar files to make sure
# it gets the latest build for specific version
LABEL vendor="Gluu Federation" \
    org.gluu.oxtrust-server.version="${OX_VERSION}" \
    org.gluu.oxtrust-server.build-date="${OX_BUILD_DATE}"

# Install oxTrust
RUN wget -q ${OXTRUST_DOWNLOAD_URL} -O /tmp/oxtrust.war \
    && mkdir -p ${JETTY_BASE}/identity/webapps/identity \
    && unzip -qq /tmp/oxtrust.war -d ${JETTY_BASE}/identity/webapps/identity \
    && java -jar ${JETTY_HOME}/start.jar jetty.home=${JETTY_HOME} jetty.base=${JETTY_BASE}/identity --add-to-start=server,deploy,annotations,resources,http,http-forwarded,jsp,ext,websocket \
    && rm -f /tmp/oxtrust.war \
    && mkdir -p ${JETTY_BASE}/identity/conf \
    && unzip -q ${JETTY_BASE}/identity/webapps/identity/WEB-INF/lib/oxtrust-configuration-${OX_VERSION}.jar shibboleth3/* -d /opt/gluu/jetty/identity/conf \
    && mv ${JETTY_BASE}/identity/webapps/identity/WEB-INF/web.xml ${JETTY_BASE}/identity/webapps/identity/WEB-INF/web.xml.bak

COPY jetty/web.xml ${JETTY_BASE}/identity/webapps/identity/WEB-INF/

# ======
# Facter
# ======

RUN gem install facter --no-ri --no-rdoc

# ====
# Tini
# ====

ENV TINI_VERSION v0.18.0
RUN wget -q https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini-static -O /usr/bin/tini \
    && chmod +x /usr/bin/tini

# ======
# Python
# ======

COPY requirements.txt /tmp/requirements.txt
RUN pip install -U pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

# ==========
# misc stuff
# ==========

RUN mkdir -p /etc/certs \
    && mkdir -p /etc/gluu/conf \
    && mkdir -p /var/ox/photos /var/ox/identity/removed /var/ox/identity/cr-snapshots \
    && mkdir -p ${JETTY_BASE}/identity/custom/pages ${JETTY_BASE}/identity/custom/static \
    && mkdir -p ${JETTY_BASE}/identity/custom/i18n ${JETTY_BASE}/identity/custom/libs \
    && mkdir -p /opt/scripts \
    && mkdir -p /opt/templates

# Copy templates
COPY jetty/identity_web_resources.xml ${JETTY_BASE}/identity/webapps/
COPY jetty/idp-metadata.xml.vm ${JETTY_BASE}/identity/conf/shibboleth3/idp/idp-metadata.xml.vm
COPY conf/oxTrustLogRotationConfiguration.xml /etc/gluu/conf/
COPY conf/ox-ldap.properties.tmpl /opt/templates/
COPY conf/salt.tmpl /opt/templates/


ENV GLUU_CONFIG_ADAPTER consul
ENV GLUU_CONSUL_HOST localhost
ENV GLUU_CONSUL_PORT 8500
ENV GLUU_CONSUL_CONSISTENCY stale
ENV GLUU_CONSUL_SCHEME http
ENV GLUU_CONSUL_VERIFY false
ENV GLUU_CONSUL_CACERT_FILE /etc/certs/consul_ca.crt
ENV GLUU_CONSUL_CERT_FILE /etc/certs/consul_client.crt
ENV GLUU_CONSUL_KEY_FILE /etc/certs/consul_client.key
ENV GLUU_CONSUL_TOKEN_FILE /etc/certs/consul_token
ENV GLUU_KUBERNETES_NAMESPACE default
ENV GLUU_KUBERNETES_CONFIGMAP gluu
ENV GLUU_LDAP_URL localhost:1636
ENV GLUU_CUSTOM_OXTRUST_URL ""
ENV GLUU_SHIB_SOURCE_DIR /opt/shibboleth-idp
ENV GLUU_SHIB_TARGET_DIR /opt/shared-shibboleth-idp
ENV PYTHON_HOME=/opt/jython
ENV GLUU_MAX_RAM_FRACTION 1
ENV GLUU_OXAUTH_BACKEND localhost:8081

VOLUME ${JETTY_BASE}/identity/custom/pages
VOLUME ${JETTY_BASE}/identity/custom/static
VOLUME ${JETTY_BASE}/identity/custom/i18n
VOLUME ${JETTY_BASE}/identity/custom/libs
VOLUME ${JETTY_BASE}/identity/lib/ext
VOLUME ${JETTY_BASE}/identity/logs
VOLUME /opt/shared-shibboleth-idp

COPY scripts /opt/scripts
RUN chmod +x /opt/scripts/entrypoint.sh
ENTRYPOINT ["tini", "--"]
CMD ["/opt/scripts/wait-for-it", "/opt/scripts/entrypoint.sh"]

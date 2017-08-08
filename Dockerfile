FROM ubuntu:14.04

MAINTAINER Gluu Inc. <support@gluu.org>

# ===============
# Ubuntu packages
# ===============

# Jetty requires Java 8, hence we need to get latest OpenJDK 8 from PPA
RUN echo "deb http://ppa.launchpad.net/openjdk-r/ppa/ubuntu trusty main" >> /etc/apt/sources.list.d/openjdk.list \
    && echo "deb-src http://ppa.launchpad.net/openjdk-r/ppa/ubuntu trusty main" >> /etc/apt/sources.list.d/openjdk.list \
    && apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 86F44E2A

RUN apt-get update && apt-get install -y \
    openjdk-8-jre-headless \
    unzip \
    wget \
    python \
    python-pip \
    facter \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# workaround for bug on ubuntu 14.04 with openjdk-8
RUN /var/lib/dpkg/info/ca-certificates-java.postinst configure

# Set openjdk 8 as default java
RUN cd /usr/lib/jvm && ln -s java-1.8.0-openjdk-amd64 default-java

# =====
# Jetty
# =====

ENV JETTY_VERSION 9.3.14.v20161028
ENV JETTY_TGZ_URL https://repo1.maven.org/maven2/org/eclipse/jetty/jetty-distribution/${JETTY_VERSION}/jetty-distribution-${JETTY_VERSION}.tar.gz
ENV JETTY_HOME /opt/jetty
ENV JETTY_BASE /opt/gluu/jetty
ENV JETTY_USER_HOME_LIB /home/jetty/lib

# Install jetty
RUN wget -q ${JETTY_TGZ_URL} -O /tmp/jetty.tar.gz \
    && tar -xzf /tmp/jetty.tar.gz -C /opt \
    && mv /opt/jetty-distribution-${JETTY_VERSION} ${JETTY_HOME} \
    && rm -rf /tmp/jetty.tar.gz

RUN mv ${JETTY_HOME}/etc/webdefault.xml ${JETTY_HOME}/etc/webdefault.xml.bak \
    && mv ${JETTY_HOME}/etc/jetty.xml ${JETTY_HOME}/etc/jetty.xml.bak
COPY jetty/webdefault.xml ${JETTY_HOME}/etc/
COPY jetty/jetty.xml ${JETTY_HOME}/etc/

# Ports required by jetty
EXPOSE 8080

# ======
# Jython
# ======

ENV JYTHON_VERSION 2.7.0
ENV JYTHON_DOWNLOAD_URL http://central.maven.org/maven2/org/python/jython-standalone/${JYTHON_VERSION}/jython-standalone-${JYTHON_VERSION}.jar

# Install Jython
RUN wget -q ${JYTHON_DOWNLOAD_URL} -O /tmp/jython.jar \
    && unzip -q /tmp/jython.jar -d /opt/jython \
    && rm -f /tmp/jython.jar

# =======
# oxTrust
# =======

ENV OX_VERSION 3.0.1
ENV OX_BUILD_DATE 2017-02-24
ENV OXTRUST_DOWNLOAD_URL https://ox.gluu.org/maven/org/xdi/oxtrust-server/${OX_VERSION}/oxtrust-server-${OX_VERSION}.war

# the LABEL defined before downloading ox war/jar files to make sure
# it gets the latest build for specific version
LABEL vendor="Gluu Federation" \
      org.gluu.oxtrust-server.version="${OX_VERSION}" \
      org.gluu.oxtrust-server.build-date="${OX_BUILD_DATE}"

# Install oxTrust
RUN wget -q ${OXTRUST_DOWNLOAD_URL} -O /tmp/oxtrust.war \
    && mkdir -p ${JETTY_BASE}/identity/webapps \
    && unzip -qq /tmp/oxtrust.war -d ${JETTY_BASE}/identity/webapps/identity \
    && java -jar ${JETTY_HOME}/start.jar jetty.home=${JETTY_HOME} jetty.base=${JETTY_BASE}/identity --add-to-start=deploy,http,jsp,ext,http-forwarded \
    && rm -f /tmp/oxtrust.war

RUN mkdir -p ${JETTY_USER_HOME_LIB}
RUN wget -q http://central.maven.org/maven2/org/bouncycastle/bcprov-jdk16/1.46/bcprov-jdk16-1.46.jar -O ${JETTY_USER_HOME_LIB}/bcprov-jdk16-1.46.jar

# Unpack Shib config
RUN unzip -q ${JETTY_BASE}/identity/webapps/identity/WEB-INF/lib/oxtrust-configuration-${OX_VERSION}.jar shibboleth3/* -d /opt/gluu/jetty/identity/conf

# ====
# tini
# ====

ENV TINI_VERSION v0.15.0
RUN wget -q https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini -O /tini \
    && chmod +x /tini
ENTRYPOINT ["/tini", "--"]

# ====
# gosu
# ====

ENV GOSU_VERSION 1.10
RUN wget -q https://github.com/tianon/gosu/releases/download/${GOSU_VERSION}/gosu-amd64 -O /usr/local/bin/gosu \
    && chmod +x /usr/local/bin/gosu

# Python packages
RUN pip install -U pip

# A workaround to address https://github.com/docker/docker-py/issues/1054
# and to make sure latest pip is being used, not from OS one
ENV PYTHONPATH="/usr/local/lib/python2.7/dist-packages:/usr/lib/python2.7/dist-packages"

RUN pip install "consulate==0.6.0"

# ==========
# misc stuff
# ==========

RUN mkdir -p /etc/certs \
    && mkdir -p /etc/gluu/conf \
    && mkdir -p /var/ox/photos /var/ox/identity/removed /var/ox/identity/cr-snapshots \
    && mkdir -p ${JETTY_BASE}/identity/custom/pages ${JETTY_BASE}/identity/custom/static \
    && mkdir -p /opt/scripts \
    && mkdir -p /opt/templates

# Copy templates
COPY jetty/identity_web_resources.xml ${JETTY_BASE}/identity/webapps/
COPY conf/oxTrustLogRotationConfiguration.xml /etc/gluu/conf/
COPY conf/ox-ldap.properties.tmpl /opt/templates/
COPY conf/salt.tmpl /opt/templates/

ENV GLUU_LDAP_URL localhost:1636
ENV GLUU_KV_HOST localhost
ENV GLUU_KV_PORT 8500
ENV GLUU_CUSTOM_OXTRUST_URL ""

VOLUME ${JETTY_BASE}/identity/custom/pages
VOLUME ${JETTY_BASE}/identity/custom/static
VOLUME ${JETTY_BASE}/identity/lib/ext


COPY scripts/entrypoint.sh /opt/scripts/
COPY scripts/entrypoint.py /opt/scripts/
RUN chmod +x /opt/scripts/entrypoint.sh
CMD ["/opt/scripts/entrypoint.sh"]

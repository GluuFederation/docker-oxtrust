import base64
import glob
import os
import re

from pygluu.containerlib import get_manager
from pygluu.containerlib.persistence import render_salt
from pygluu.containerlib.persistence import render_gluu_properties
from pygluu.containerlib.persistence import render_ldap_properties
from pygluu.containerlib.persistence import render_couchbase_properties
from pygluu.containerlib.persistence import render_hybrid_properties
from pygluu.containerlib.persistence import sync_ldap_truststore
# from pygluu.containerlib.persistence import sync_couchbase_cert
from pygluu.containerlib.persistence import sync_couchbase_truststore
from pygluu.containerlib.utils import cert_to_truststore
from pygluu.containerlib.utils import get_server_certificate

manager = get_manager()


def modify_jetty_xml():
    fn = "/opt/jetty/etc/jetty.xml"
    with open(fn) as f:
        txt = f.read()

    # disable contexts
    updates = re.sub(
        r'<New id="DefaultHandler" class="org.eclipse.jetty.server.handler.DefaultHandler"/>',
        r'<New id="DefaultHandler" class="org.eclipse.jetty.server.handler.DefaultHandler">\n\t\t\t\t <Set name="showContexts">false</Set>\n\t\t\t </New>',
        txt,
        flags=re.DOTALL | re.M,
    )

    # disable Jetty version info
    updates = re.sub(
        r'(<Set name="sendServerVersion"><Property name="jetty.httpConfig.sendServerVersion" deprecated="jetty.send.server.version" default=")true(" /></Set>)',
        r'\1false\2',
        updates,
        flags=re.DOTALL | re.M,
    )

    with open(fn, "w") as f:
        f.write(updates)


def modify_webdefault_xml():
    fn = "/opt/jetty/etc/webdefault.xml"
    with open(fn) as f:
        txt = f.read()

    # disable dirAllowed
    updates = re.sub(
        r'(<param-name>dirAllowed</param-name>)(\s*)(<param-value>)true(</param-value>)',
        r'\1\2\3false\4',
        txt,
        flags=re.DOTALL | re.M,
    )

    with open(fn, "w") as f:
        f.write(updates)


def modify_identity_xml():
    fn = "/opt/gluu/jetty/identity/webapps/identity.xml"

    with open(fn) as f:
        txt = f.read()

    with open(fn, "w") as f:
        ctx = {
            "extra_classpath": ",".join([
                j.replace("/opt/gluu/jetty/identity", ".")
                for j in glob.iglob("/opt/gluu/jetty/identity/custom/libs/*.jar")
            ])
        }
        f.write(txt % ctx)


# def patch_finishlogin_xhtml():
#     patch = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
# <f:view xmlns="http://www.w3.org/1999/xhtml" xmlns:f="http://xmlns.jcp.org/jsf/core" contentType="text/html"
#         locale="#{language.localeCode}"
#         xmlns:gluufn="http://www.gluu.org/jsf/functions">
#     <f:metadata>
#         <f:viewAction action="#{authenticator.authenticate}" if="#{(gluufn:trim(identity.oauthData.userUid) ne null) and (gluufn:trim(identity.oauthData.userUid) ne '')}" onPostback="false"/>
#     </f:metadata>
# </f:view>"""

#     finishlogin_xhtml = "/opt/gluu/jetty/identity/webapps/identity/finishlogin.xhtml"
#     with open(finishlogin_xhtml, "w") as f:
#         f.write(patch)


if __name__ == "__main__":
    persistence_type = os.environ.get("GLUU_PERSISTENCE_TYPE", "ldap")

    render_salt(manager, "/app/templates/salt.tmpl", "/etc/gluu/conf/salt")
    render_gluu_properties("/app/templates/gluu.properties.tmpl", "/etc/gluu/conf/gluu.properties")

    if persistence_type in ("ldap", "hybrid"):
        render_ldap_properties(
            manager,
            "/app/templates/gluu-ldap.properties.tmpl",
            "/etc/gluu/conf/gluu-ldap.properties",
        )
        manager.secret.to_file(
            "ldap_ssl_cert",
            "/etc/certs/opendj.crt",
            decode=True,
        )
        sync_ldap_truststore(manager)

    if persistence_type in ("couchbase", "hybrid"):
        render_couchbase_properties(
            manager,
            "/app/templates/gluu-couchbase.properties.tmpl",
            "/etc/gluu/conf/gluu-couchbase.properties",
        )
        # sync_couchbase_cert(manager)
        sync_couchbase_truststore(manager)

    if persistence_type == "hybrid":
        render_hybrid_properties("/etc/gluu/conf/gluu-hybrid.properties")

    if not os.path.isfile("/etc/certs/gluu_https.crt"):
        get_server_certificate(manager.config.get("hostname"), 443, "/etc/certs/gluu_https.crt")

    cert_to_truststore(
        "gluu_https",
        "/etc/certs/gluu_https.crt",
        "/usr/lib/jvm/default-jvm/jre/lib/security/cacerts",
        "changeit",
    )

    if not os.path.isfile("/etc/certs/shibIDP.crt"):
        manager.secret.to_file("shibIDP_cert", "/etc/certs/shibIDP.crt", decode=True)

    if not os.path.isfile("/etc/certs/shibIDP.key"):
        manager.secret.to_file("shibIDP_key", "/etc/certs/shibIDP.key", decode=True)

    if not os.path.isfile("/etc/certs/idp-signing.crt"):
        manager.secret.to_file("idp3SigningCertificateText", "/etc/certs/idp-signing.crt")

    if not os.path.isfile("/etc/certs/idp-encryption.crt"):
        manager.secret.to_file("idp3EncryptionCertificateText", "/etc/certs/idp-encryption.crt")

    manager.secret.to_file(
        "scim_rs_jks_base64",
        manager.config.get("scim_rs_client_jks_fn"),
        decode=True,
        binary_mode=True,
    )
    manager.secret.to_file(
        "passport_rs_jks_base64",
        manager.config.get("passport_rs_client_jks_fn"),
        decode=True,
        binary_mode=True,
    )

    manager.secret.to_file(
        "api_rs_jks_base64",
        manager.config.get("api_rs_client_jks_fn"),
        decode=True,
        binary_mode=True,
    )
    with open(manager.config.get("api_rs_client_jwks_fn"), "w") as f:
        f.write(
            base64.b64decode(manager.secret.get("api_rs_client_base64_jwks")).decode()
        )

    manager.secret.to_file(
        "api_rp_jks_base64",
        manager.config.get("api_rp_client_jks_fn"),
        decode=True,
        binary_mode=True,
    )
    with open(manager.config.get("api_rp_client_jwks_fn"), "w") as f:
        f.write(
            base64.b64decode(manager.secret.get("api_rp_client_base64_jwks")).decode()
        )

    manager.secret.to_file("scim_rs_jks_base64", "/etc/certs/scim-rs.jks",
                           decode=True, binary_mode=True)
    with open(manager.config.get("scim_rs_client_jwks_fn"), "w") as f:
        f.write(
            base64.b64decode(manager.secret.get("scim_rs_client_base64_jwks")).decode()
        )

    manager.secret.to_file("scim_rp_jks_base64", "/etc/certs/scim-rp.jks",
                           decode=True, binary_mode=True)
    with open(manager.config.get("scim_rp_client_jwks_fn"), "w") as f:
        f.write(
            base64.b64decode(manager.secret.get("scim_rp_client_base64_jwks")).decode()
        )

    modify_jetty_xml()
    modify_webdefault_xml()
    modify_identity_xml()
    # patch_finishlogin_xhtml()

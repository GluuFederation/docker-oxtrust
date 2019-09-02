import os
import re

from pygluu.containerlib import get_manager

GLUU_LDAP_URL = os.environ.get("GLUU_LDAP_URL", "localhost:1636")
GLUU_COUCHBASE_URL = os.environ.get("GLUU_COUCHBASE_URL", "localhost")
GLUU_PERSISTENCE_TYPE = os.environ.get("GLUU_PERSISTENCE_TYPE", "ldap")
GLUU_PERSISTENCE_LDAP_MAPPING = os.environ.get("GLUU_PERSISTENCE_LDAP_MAPPING", "default")

manager = get_manager()


def render_salt():
    encode_salt = manager.secret.get("encoded_salt")

    with open("/app/templates/salt.tmpl") as fr:
        txt = fr.read()
        with open("/etc/gluu/conf/salt", "w") as fw:
            rendered_txt = txt % {"encode_salt": encode_salt}
            fw.write(rendered_txt)


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


def patch_finishlogin_xhtml():
    patch = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<f:view xmlns="http://www.w3.org/1999/xhtml" xmlns:f="http://xmlns.jcp.org/jsf/core" contentType="text/html"
        locale="#{language.localeCode}"
        xmlns:gluufn="http://www.gluu.org/jsf/functions">
    <f:metadata>
        <f:viewAction action="#{authenticator.authenticate}" if="#{(gluufn:trim(identity.oauthData.userUid) ne null) and (gluufn:trim(identity.oauthData.userUid) ne '')}" onPostback="false"/>
    </f:metadata>
</f:view>"""

    finishlogin_xhtml = "/opt/gluu/jetty/identity/webapps/identity/finishlogin.xhtml"
    with open(finishlogin_xhtml, "w") as f:
        f.write(patch)


def render_gluu_properties():
    with open("/app/templates/gluu.properties.tmpl") as fr:
        txt = fr.read()

        ldap_hostname, ldaps_port = GLUU_LDAP_URL.split(":")

        with open("/etc/gluu/conf/gluu.properties", "w") as fw:
            rendered_txt = txt % {
                "gluuOptPythonFolder": "/opt/gluu/python",
                "certFolder": "/etc/certs",
                "persistence_type": GLUU_PERSISTENCE_TYPE,
            }
            fw.write(rendered_txt)


def render_ldap_properties():
    with open("/app/templates/gluu-ldap.properties.tmpl") as fr:
        txt = fr.read()

        ldap_hostname, ldaps_port = GLUU_LDAP_URL.split(":")

        with open("/etc/gluu/conf/gluu-ldap.properties", "w") as fw:
            rendered_txt = txt % {
                "ldap_binddn": manager.config.get("ldap_binddn"),
                "encoded_ox_ldap_pw": manager.secret.get("encoded_ox_ldap_pw"),
                "ldap_hostname": ldap_hostname,
                "ldaps_port": ldaps_port,
                "ldapTrustStoreFn": manager.config.get("ldapTrustStoreFn"),
                "encoded_ldapTrustStorePass": manager.secret.get("encoded_ldapTrustStorePass"),
            }
            fw.write(rendered_txt)


def get_couchbase_mappings():
    mappings = {
        "default": {
            "bucket": "gluu",
            "mapping": "",
        },
        "user": {
            "bucket": "gluu_user",
            "mapping": "people, groups, authorizations"
        },
        "cache": {
            "bucket": "gluu_cache",
            "mapping": "cache",
        },
        "site": {
            "bucket": "gluu_site",
            "mapping": "cache-refresh",
        },
        "token": {
            "bucket": "gluu_token",
            "mapping": "tokens"
        },
    }

    if GLUU_PERSISTENCE_TYPE == "hybrid":
        mappings = {
            name: mapping for name, mapping in mappings.iteritems()
            if name != GLUU_PERSISTENCE_LDAP_MAPPING
        }

    return mappings


def render_couchbase_properties():
    _couchbase_mappings = get_couchbase_mappings()
    couchbase_buckets = []
    couchbase_mappings = []

    for _, mapping in _couchbase_mappings.iteritems():
        couchbase_buckets.append(mapping["bucket"])

        if not mapping["mapping"]:
            continue

        couchbase_mappings.append("bucket.{0}.mapping: {1}".format(
            mapping["bucket"], mapping["mapping"],
        ))

    # always have `gluu` as default bucket
    if "gluu" not in couchbase_buckets:
        couchbase_buckets.insert(0, "gluu")

    with open("/app/templates/gluu-couchbase.properties.tmpl") as fr:
        txt = fr.read()

        ldap_hostname, ldaps_port = GLUU_LDAP_URL.split(":")

        with open("/etc/gluu/conf/gluu-couchbase.properties", "w") as fw:
            rendered_txt = txt % {
                "hostname": GLUU_COUCHBASE_URL,
                "couchbase_server_user": manager.config.get("couchbase_server_user"),
                "encoded_couchbase_server_pw": manager.secret.get("encoded_couchbase_server_pw"),
                "couchbase_buckets": ", ".join(couchbase_buckets),
                "default_bucket": "gluu",
                "couchbase_mappings": "\n".join(couchbase_mappings),
                "encryption_method": "SSHA-256",
                "ssl_enabled": "true",
                "couchbaseTrustStoreFn": manager.config.get("couchbaseTrustStoreFn"),
                "encoded_couchbaseTrustStorePass": manager.secret.get("encoded_couchbaseTrustStorePass"),
            }
            fw.write(rendered_txt)


def render_hybrid_properties():
    _couchbase_mappings = get_couchbase_mappings()

    ldap_mapping = GLUU_PERSISTENCE_LDAP_MAPPING

    if GLUU_PERSISTENCE_LDAP_MAPPING == "default":
        default_storage = "ldap"
    else:
        default_storage = "couchbase"

    couchbase_mappings = [
        mapping["mapping"] for name, mapping in _couchbase_mappings.iteritems()
        if name != ldap_mapping
    ]

    out = "\n".join([
        "storages: ldap, couchbase",
        "storage.default: {}".format(default_storage),
        "storage.ldap.mapping: {}".format(ldap_mapping),
        "storage.couchbase.mapping: {}".format(
            ", ".join(filter(None, couchbase_mappings))
        ),
    ]).replace("user", "people, groups")

    with open("/etc/gluu/conf/gluu-hybrid.properties", "w") as fw:
        fw.write(out)


if __name__ == "__main__":
    render_salt()
    render_gluu_properties()

    if GLUU_PERSISTENCE_TYPE in ("ldap", "hybrid"):
        render_ldap_properties()
        manager.secret.to_file(
            "ldap_pkcs12_base64",
            manager.config.get("ldapTrustStoreFn"),
            decode=True,
            binary_mode=True,
        )

    if GLUU_PERSISTENCE_TYPE in ("couchbase", "hybrid"):
        render_couchbase_properties()
        manager.secret.to_file(
            "couchbase_pkcs12_base64",
            manager.config.get("couchbaseTrustStoreFn"),
            decode=True,
            binary_mode=True,
        )

    if GLUU_PERSISTENCE_TYPE == "hybrid":
        render_hybrid_properties()

    manager.secret.to_file("ssl_cert", "/etc/certs/gluu_https.crt")
    manager.secret.to_file("ssl_key", "/etc/certs/gluu_https.key")

    manager.secret.to_file("shibIDP_cert", "/etc/certs/shibIDP.crt", decode=True)
    manager.secret.to_file("shibIDP_key", "/etc/certs/shibIDP.key", decode=True)
    manager.secret.to_file("idp3SigningCertificateText", "/etc/certs/idp-signing.crt")
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

    modify_jetty_xml()
    modify_webdefault_xml()
    patch_finishlogin_xhtml()

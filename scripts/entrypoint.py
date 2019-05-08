import base64
import os
import re

import pyDes

from gluulib import get_manager

GLUU_LDAP_URL = os.environ.get("GLUU_LDAP_URL", "localhost:1636")

manager = get_manager()


def render_salt():
    encode_salt = manager.secret.get("encoded_salt")

    with open("/opt/templates/salt.tmpl") as fr:
        txt = fr.read()
        with open("/etc/gluu/conf/salt", "w") as fw:
            rendered_txt = txt % {"encode_salt": encode_salt}
            fw.write(rendered_txt)


def render_ldap_properties():
    with open("/opt/templates/ox-ldap.properties.tmpl") as fr:
        txt = fr.read()

        with open("/etc/gluu/conf/ox-ldap.properties", "w") as fw:
            rendered_txt = txt % {
                "ldap_binddn": manager.config.get("ldap_binddn"),
                "encoded_ox_ldap_pw": manager.secret.get("encoded_ox_ldap_pw"),
                "inumAppliance": manager.config.get("inumAppliance"),
                "ldap_url": GLUU_LDAP_URL,
                "ldapTrustStoreFn": manager.config.get("ldapTrustStoreFn"),
                "encoded_ldapTrustStorePass": manager.secret.get("encoded_ldapTrustStorePass"),
            }
            fw.write(rendered_txt)


def render_ssl_cert():
    ssl_cert = manager.secret.get("ssl_cert")
    if ssl_cert:
        with open("/etc/certs/gluu_https.crt", "w") as fd:
            fd.write(ssl_cert)


def render_ssl_key():
    ssl_key = manager.secret.get("ssl_key")
    if ssl_key:
        with open("/etc/certs/gluu_https.key", "w") as fd:
            fd.write(ssl_key)


def decrypt_text(encrypted_text, key):
    cipher = pyDes.triple_des(b"{}".format(key), pyDes.ECB,
                              padmode=pyDes.PAD_PKCS5)
    encrypted_text = b"{}".format(base64.b64decode(encrypted_text))
    return cipher.decrypt(encrypted_text)


def sync_ldap_pkcs12():
    pkcs = decrypt_text(manager.secret.get("ldap_pkcs12_base64"),
                        manager.secret.get("encoded_salt"))

    with open(manager.config.get("ldapTrustStoreFn"), "wb") as fw:
        fw.write(pkcs)


def sync_ldap_cert():
    cert = decrypt_text(manager.secret.get("ldap_ssl_cert"),
                        manager.secret.get("encoded_salt"))

    ldap_type = manager.config.get("ldap_type")
    if ldap_type == "opendj":
        cert_fn = "/etc/certs/opendj.crt"
    else:
        cert_fn = "/etc/certs/openldap.crt"

    with open(cert_fn, "wb") as fw:
        fw.write(cert)


def render_idp_cert():
    cert = decrypt_text(manager.secret.get("shibIDP_cert"), manager.secret.get("encoded_salt"))
    with open("/etc/certs/shibIDP.crt", "w") as fd:
        fd.write(cert)


def render_idp_key():
    cert = decrypt_text(manager.secret.get("shibIDP_key"), manager.secret.get("encoded_salt"))
    with open("/etc/certs/shibIDP.key", "w") as fd:
        fd.write(cert)


def render_idp_signing_cert():
    cert = manager.secret.get("idp3SigningCertificateText")
    with open("/etc/certs/idp-signing.crt", "w") as fd:
        fd.write(cert)


def render_idp_encryption_cert():
    cert = manager.secret.get("idp3EncryptionCertificateText")
    with open("/etc/certs/idp-encryption.crt", "w") as fd:
        fd.write(cert)


def render_scim_rs_jks():
    jks = decrypt_text(manager.secret.get("scim_rs_jks_base64"),
                       manager.secret.get("encoded_salt"))
    with open(manager.config.get("scim_rs_client_jks_fn"), "w") as f:
        f.write(jks)


def render_passport_rs_jks():
    jks = decrypt_text(manager.secret.get("passport_rs_jks_base64"),
                       manager.secret.get("encoded_salt"))
    with open(manager.config.get("passport_rs_client_jks_fn"), "w") as f:
        f.write(jks)


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


if __name__ == "__main__":
    render_salt()
    render_ldap_properties()
    render_ssl_cert()
    render_ssl_key()
    render_idp_cert()
    render_idp_key()
    render_idp_signing_cert()
    render_idp_encryption_cert()
    render_scim_rs_jks()
    render_passport_rs_jks()
    sync_ldap_pkcs12()
    sync_ldap_cert()
    modify_jetty_xml()
    modify_webdefault_xml()
    patch_finishlogin_xhtml()

import base64
import os

import pyDes
from gluu_config import ConfigManager

GLUU_LDAP_URL = os.environ.get("GLUU_LDAP_URL", "localhost:1636")

config_manager = ConfigManager()


def render_salt():
    encode_salt = config_manager.get("encoded_salt")

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
                "ldap_binddn": config_manager.get("ldap_binddn"),
                "encoded_ox_ldap_pw": config_manager.get("encoded_ox_ldap_pw"),
                "inumAppliance": config_manager.get("inumAppliance"),
                "ldap_url": GLUU_LDAP_URL,
                "ldapTrustStoreFn": config_manager.get("ldapTrustStoreFn"),
                "encoded_ldapTrustStorePass": config_manager.get("encoded_ldapTrustStorePass"),
            }
            fw.write(rendered_txt)


def render_ssl_cert():
    ssl_cert = config_manager.get("ssl_cert")
    if ssl_cert:
        with open("/etc/certs/gluu_https.crt", "w") as fd:
            fd.write(ssl_cert)


def render_ssl_key():
    ssl_key = config_manager.get("ssl_key")
    if ssl_key:
        with open("/etc/certs/gluu_https.key", "w") as fd:
            fd.write(ssl_key)


def decrypt_text(encrypted_text, key):
    cipher = pyDes.triple_des(b"{}".format(key), pyDes.ECB,
                              padmode=pyDes.PAD_PKCS5)
    encrypted_text = b"{}".format(base64.b64decode(encrypted_text))
    return cipher.decrypt(encrypted_text)


def sync_ldap_pkcs12():
    pkcs = decrypt_text(config_manager.get("ldap_pkcs12_base64"),
                        config_manager.get("encoded_salt"))

    with open(config_manager.get("ldapTrustStoreFn"), "wb") as fw:
        fw.write(pkcs)


def sync_ldap_cert():
    cert = decrypt_text(config_manager.get("ldap_ssl_cert"),
                        config_manager.get("encoded_salt"))
    ldap_type = config_manager.get("ldap_type")
    if ldap_type == "opendj":
        cert_fn = "/etc/certs/opendj.crt"
    else:
        cert_fn = "/etc/certs/openldap.crt"
    with open(cert_fn, "wb") as fw:
        fw.write(cert)


def render_idp_cert():
    cert = decrypt_text(config_manager.get("shibIDP_cert"), config_manager.get("encoded_salt"))
    with open("/etc/certs/shibIDP.crt", "w") as fd:
        fd.write(cert)


def render_idp_key():
    cert = decrypt_text(config_manager.get("shibIDP_key"), config_manager.get("encoded_salt"))
    with open("/etc/certs/shibIDP.key", "w") as fd:
        fd.write(cert)


def render_idp_signing_cert():
    cert = config_manager.get("idp3SigningCertificateText")
    with open("/etc/certs/idp-signing.crt", "w") as fd:
        fd.write(cert)


def render_idp_encryption_cert():
    cert = config_manager.get("idp3EncryptionCertificateText")
    with open("/etc/certs/idp-encryption.crt", "w") as fd:
        fd.write(cert)


def render_scim_rs_jks():
    jks = decrypt_text(config_manager.get("scim_rs_jks_base64"),
                       config_manager.get("encoded_salt"))
    with open(config_manager.get("scim_rs_client_jks_fn"), "w") as f:
        f.write(jks)


def render_passport_rs_jks():
    jks = decrypt_text(config_manager.get("passport_rs_jks_base64"),
                       config_manager.get("encoded_salt"))
    with open(config_manager.get("passport_rs_client_jks_fn"), "w") as f:
        f.write(jks)


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

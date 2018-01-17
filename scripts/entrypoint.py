import base64
import os

import consulate
from M2Crypto.EVP import Cipher

GLUU_LDAP_URL = os.environ.get("GLUU_LDAP_URL", "localhost:1636")
GLUU_KV_HOST = os.environ.get("GLUU_KV_HOST", "localhost")
GLUU_KV_PORT = os.environ.get("GLUU_KV_PORT", 8500)

consul = consulate.Consul(host=GLUU_KV_HOST, port=GLUU_KV_PORT)


def render_salt():
    encode_salt = consul.kv.get("encoded_salt")

    with open("/opt/templates/salt.tmpl") as fr:
        txt = fr.read()
        with open("/etc/gluu/conf/salt", "w") as fw:
            rendered_txt = txt % {"encode_salt": encode_salt}
            fw.write(rendered_txt)


def render_ldap_properties():
    ldap_binddn = consul.kv.get("ldap_binddn")
    encoded_ox_ldap_pw = consul.kv.get("encoded_ox_ldap_pw")
    inumAppliance = consul.kv.get("inumAppliance")
    use_ssl = consul.kv.get("ldap_use_ssl", "false")
    encoded_openldapJksPass = consul.kv.get("encoded_openldapJksPass")

    with open("/opt/templates/ox-ldap.properties.tmpl") as fr:
        txt = fr.read()

        with open("/etc/gluu/conf/ox-ldap.properties", "w") as fw:
            rendered_txt = txt % {
                "ldap_binddn": ldap_binddn,
                "encoded_ox_ldap_pw": encoded_ox_ldap_pw,
                "inumAppliance": inumAppliance,
                "ldap_url": GLUU_LDAP_URL,
                "use_ssl": use_ssl,
                "encoded_openldapJksPass": encoded_openldapJksPass,
            }
            fw.write(rendered_txt)


def render_ssl_cert():
    ssl_cert = consul.kv.get("ssl_cert")
    if ssl_cert:
        with open("/etc/certs/gluu_https.crt", "w") as fd:
            fd.write(ssl_cert)


def render_ssl_key():
    ssl_key = consul.kv.get("ssl_key")
    if ssl_key:
        with open("/etc/certs/gluu_https.key", "w") as fd:
            fd.write(ssl_key)


def render_scim_rs_jks():
    jks = decrypt_text(consul.kv.get("scim_rs_jks_base64"),
                       consul.kv.get("encoded_salt"))

    with open(consul.kv.get("scim_rs_client_jks_fn"), "w") as fd:
        fd.write(jks)
        return True
    return False


def decrypt_text(encrypted_text, key):
    # Porting from pyDes-based encryption (see http://git.io/htpk)
    # to use M2Crypto instead (see https://gist.github.com/mrluanma/917014)
    cipher = Cipher(alg="des_ede3_ecb",
                    key=b"{}".format(key),
                    op=0,
                    iv="\0" * 16)
    decrypted_text = cipher.update(base64.b64decode(
        b"{}".format(encrypted_text)
    ))
    decrypted_text += cipher.final()
    return decrypted_text


if __name__ == "__main__":
    render_salt()
    render_ldap_properties()
    render_ssl_cert()
    render_ssl_key()
    render_scim_rs_jks()

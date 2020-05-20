# import glob


def modify_identity_xml():
    fn = "/opt/gluu/jetty/identity/webapps/identity.xml"

    with open(fn) as f:
        txt = f.read()

    with open(fn, "w") as f:
        ctx = {
            # "extra_classpath": ",".join([
            #     j.replace("/opt/gluu/jetty/identity", ".")
            #     for j in glob.iglob("/opt/gluu/jetty/identity/custom/libs/*.jar")
            # ])
            # oxtrust-api-server 4.2 is broken
            "extra_classpath": "",
        }
        f.write(txt % ctx)


if __name__ == "__main__":
    modify_identity_xml()

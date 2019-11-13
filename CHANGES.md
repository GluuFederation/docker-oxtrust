# Changelog

Here you can see an overview of changes between each release.

## Version 4.0.1_03

Released on November 14th, 2019.

* Upgraded `pygluu-containerlib` to show connection issue with Couchbase explicitly.
* Upgraded to oxTrust v4.0.1.Final build at 2019-11-13.

## Version 4.0.1_02

Released on November 5th, 2019.

* Added oxTrust API endpoints (disabled by default).

## Version 4.0.1_01

Released on November 1st, 2019.

* Upgraded to Gluu Server 4.0.1.

## Version 4.0.0_01

Released on October 22nd, 2019.

* Upgraded to Gluu Server 4.0.
* Fixed minor issue in UI where some of the certificate info are missing.

## Version 3.1.6_03

Released on May 10th, 2019.

* Alpine upgraded to v3.9. Ref: https://github.com/GluuFederation/gluu-docker/issues/71.

## Version 3.1.6_02

Released on May 8th, 2019.

* Added security patch for oxTrust. Reference: https://github.com/GluuFederation/docker-oxtrust/issues/13.

## Version 3.1.6_01

Released on April 29th, 2019.

* Upgraded to Gluu Server 3.1.6.

## Version 3.1.5_04

Released on May 10th, 2019.

* Alpine upgraded to v3.9. Ref: https://github.com/GluuFederation/gluu-docker/issues/71.

## Version 3.1.5_03

Released on May 8th, 2019.

* Added security patch for oxTrust. Reference: https://github.com/GluuFederation/docker-oxtrust/issues/13.

## Version 3.1.5_02

Released on April 9th, 2019.

* Added license info on container startup.
* Disabled `sendServerVersion` config of Jetty server.
* Upgraded `oxtrust-server.war` to 3.1.5.sp1.

## Version 3.1.5_01

Released on March 23rd, 2019.

* Upgraded to Gluu Server 3.1.5.

## Version 3.1.4_02

Released on January 16th, 2019.

* Added `http-forwarded` module to Jetty.

## Version 3.1.4_01

Released on November 12th, 2018.

* Upgraded to Gluu Server 3.1.4.

## Version 3.1.3_08

Released on September 24th, 2018.

* Added missing certificates `httpd.crt` and `opendj.crt`/`openldap.crt`.

## Version 3.1.3_07

Released on September 18th, 2018.

* Changed base image to use Alpine 3.8.1.

## Version 3.1.3_06

Released on September 12th, 2018.

* Added feature to connect to secure Consul (HTTPS).

## Version 3.1.3_05

Released on August 31st, 2018.

* Added Tini to handle signal forwarding and reaping zombie processes.

## Version 3.1.3_04

Released on August 24th, 2018.

* Added patches for Richfaces libraries.

## Version 3.1.3_03

Released on July 31st, 2018.

* Added feature to enable/disable remote debugging of JVM.

## Version 3.1.3_02

Released on July 20th, 2018.

* Added wrapper to manage config via Consul KV or Kubernetes configmap.

## Version 3.1.3_01

Released on June 6th, 2018.

* Upgraded to Gluu Server 3.1.3.

## Version 3.1.2_01

Released on June 6th, 2018.

* Upgraded to Gluu Server 3.1.2.

## Version 3.1.1_rev1.0.0-beta2

Released on October 11th, 2017.

* Use latest oxtrust-server build.

## Version 3.1.1_rev1.0.0-beta1

Released on October 6th, 2017.

* Migrated to Gluu Server 3.1.1.

## Version 3.0.1_rev1.0.0-beta2

Released on July 25th, 2017.

* Fixed extraction process of custom oxTrust files where empty directories couldn't be copied to pre-defined custom directories.

## Version 3.0.1_rev1.0.0-beta1

Released on July 7th, 2017.

* Added working oxTrust v3.0.1.

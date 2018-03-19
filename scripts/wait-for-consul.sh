#! /usr/bin/env bash

## Script that executes the command you pass to it once consul is
## ready, i.e. populated.
##
## Typically used from docker-compose.yml:
##
## oxtrust:
##   image: "gluufederation/oxtrust:latest"
##   environment:
##     - GLUU_KV_HOST=consul
##     - GLUU_KV_PORT=8500
##     - GLUU_LDAP_URL=ldap:1389
##   depends_on:
##     - consul
##   command: ["/opt/scripts/wait-for-consul.sh", "--", "/opt/scripts/entrypoint.sh"]
##
## More context: https://docs.docker.com/compose/startup-order/
##
## author: torstein@escenic.com
set -o errexit
set -o nounset
set -o pipefail
shopt -s nullglob

LAST_CONSUL_VALUE_URI=${GLUU_KV_HOST-localhost}:${GLUU_KV_POR-8500}/v1/kv/oxauth_openid_jwks_fn
MAX_WAIT=240

wait_for_consul_to_be_populated() {
  # Waiting for consul to be populated
  printf "Waiting up to %s seconds for Consul to be configured: " "${MAX_WAIT}"
  for (( i = 0; i < MAX_WAIT; i++)); do
    wget -O - "${LAST_CONSUL_VALUE_URI}" &>/dev/null && break || true
    sleep 1
    printf "%s" "."
  done
  printf "\n" ""
}

main() {
  wait_for_consul_to_be_populated
  exec "${@}"
}

main "$@"

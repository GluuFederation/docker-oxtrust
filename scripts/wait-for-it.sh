#!/bin/sh

set -e

if [ -f /etc/redhat-release ]; then
    source scl_source enable python27 && python /opt/scripts/wait_for_it.py "$@"
else
    python /opt/scripts/wait_for_it.py "$@"
fi

#!/usr/bin/env python
import os
import sys

import click


def as_boolean(val, default=False):
    truthy = set(('t', 'T', 'true', 'True', 'TRUE', '1', 1, True))
    falsy = set(('f', 'F', 'false', 'False', 'FALSE', '0', 0, False))

    if val in truthy:
        return True
    if val in falsy:
        return False
    return default


def execute_passed_command(command_list):
    os.system(" ".join(command_list))


def main():
    if not os.path.isfile("/license_ack"):
        # license prompt
        GLUU_AUTO_ACCEPT_LICENSE = os.environ.get("GLUU_AUTO_ACCEPT_LICENSE", False)

        if not as_boolean(GLUU_AUTO_ACCEPT_LICENSE):
            click.echo("Gluu License Agreement: https://github.com/GluuFederation/gluu-docker/blob/3.1.4/LICENSE")
            click.echo("")

            if not click.confirm("Do you acknowledge that use of Gluu Server Docker Edition is subject to the Gluu Support License"):
                sys.exit(1)

            click.echo("")
            # create a flag
            with open("/license_ack", "w") as fw:
                fw.write("")

    # execute next command
    execute_passed_command(sys.argv[1:])


if __name__ == "__main__":
    main()

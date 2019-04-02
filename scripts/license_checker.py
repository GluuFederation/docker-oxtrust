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
    GLUU_AUTO_ACK_LICENSE = os.environ.get("GLUU_AUTO_ACK_LICENSE", False)

    # don't show a prompt if one of the following flags is true:
    # 1. `GLUU_AUTO_ACK_LICENSE` is set to truthy value
    # 2. `/licenses/ack` file is exist
    skip_prompt = any([
        as_boolean(GLUU_AUTO_ACK_LICENSE) is True,
        os.path.isfile("/licenses/ack"),
    ])

    # show a prompt (if needed)
    if not skip_prompt:
        click.echo("Gluu License Agreement: https://github.com/GluuFederation/gluu-docker/blob/3.1.4/LICENSE")

        try:
            if not click.confirm("Do you acknowledge that use of Gluu Server Docker Edition is subject to the Gluu Support License"):
                click.echo("Error: unable to proceed without license acknowledgement ... exiting")
                sys.exit(1)
        except click.exceptions.Abort:
            click.echo("")
            click.echo("Error: unable to proceed without an interactive process ... exiting")
            sys.exit(1)
        else:
            click.echo("")
            # create a flag to avoid showing the prompt again in subsequent runs
            with open("/licenses/ack", "w") as fw:
                fw.write("")

    # execute next command
    execute_passed_command(sys.argv[1:])


if __name__ == "__main__":
    main()

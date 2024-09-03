from __future__ import annotations

import argparse
from pathlib import Path

from bfabric.bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric.experimental.app_interface.input_preparation.prepare import prepare_folder


def main():
    setup_script_logging()
    client = Bfabric.from_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("action", default="prepare", choices=["prepare", "clean"])
    parser.add_argument("--inputs-yaml", type=Path, required=True)
    parser.add_argument("--target-folder", type=Path, required=False)
    parser.add_argument("--ssh-user", type=str, required=False)
    args = parser.parse_args()
    prepare_folder(
        inputs_yaml=args.inputs_yaml,
        target_folder=args.target_folder,
        ssh_user=args.ssh_user,
        client=client,
        action=args.action,
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from pathlib import Path

from bfabric.bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric.experimental.app_interface.input_preparation._spec import InputsSpec
from bfabric.experimental.app_interface.input_preparation.prepare import PrepareInputs


def prepare_folder(
    inputs_yaml: Path, target_folder: Path | None, client: Bfabric, ssh_user: str | None, action: str = "prepare"
) -> None:
    # set defaults
    inputs_yaml = inputs_yaml.absolute()
    if target_folder is None:
        target_folder = inputs_yaml.parent

    # parse the specs
    specs_list = InputsSpec.read_yaml(inputs_yaml)

    # prepare the folder
    prepare = PrepareInputs(client=client, working_dir=target_folder, ssh_user=ssh_user)
    if action == "prepare":
        prepare.prepare_all(specs=specs_list)
    elif action == "clean":
        prepare.clean_all(specs=specs_list)
    else:
        raise ValueError(f"Unknown action: {action}")


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

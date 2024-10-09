from __future__ import annotations

from pathlib import Path

import cyclopts

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric.experimental.app_interface.input_preparation import prepare_folder
from bfabric.experimental.app_interface.input_preparation.prepare import print_input_files_list

app_inputs = cyclopts.App("inputs", help="Prepare input files for an app.")


@app_inputs.command()
def prepare(
    inputs_yaml: Path,
    target_folder: Path | None = None,
    *,
    ssh_user: str | None = None,
) -> None:
    """Prepare the input files by downloading them (if necessary).

    :param inputs_yaml: Path to the inputs.yml file.
    :param target_folder: Path to the target folder where the input files should be downloaded.
    :param ssh_user: SSH user to use for downloading the input files, instead of the current user.
    """
    setup_script_logging()
    client = Bfabric.from_config()
    prepare_folder(
        inputs_yaml=inputs_yaml,
        target_folder=target_folder,
        ssh_user=ssh_user,
        client=client,
        action="prepare",
    )


@app_inputs.command()
def clean(
    inputs_yaml: Path,
    target_folder: Path | None = None,
) -> None:
    """Removes all local copies of input files.

    :param inputs_yaml: Path to the inputs.yml file.
    :param target_folder: Path to the target folder where the input files should be removed.
    """
    setup_script_logging()
    client = Bfabric.from_config()
    # TODO clean shouldn't even need all these arguments, this could be refactored later
    prepare_folder(
        inputs_yaml=inputs_yaml,
        target_folder=target_folder,
        ssh_user=None,
        action="clean",
        client=client,
    )


@app_inputs.command()
def list(
    inputs_yaml: Path,
    target_folder: Path | None = None,
) -> None:
    """Lists the input files for an app."""
    setup_script_logging()
    client = Bfabric.from_config()
    print_input_files_list(inputs_yaml=inputs_yaml, target_folder=target_folder, client=client)

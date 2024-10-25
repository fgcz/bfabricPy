from __future__ import annotations

from pathlib import Path

import cyclopts

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from app_runner.input_preparation import prepare_folder
from app_runner.input_preparation.spec import InputsSpec
from app_runner.input_preparation.integrity import IntegrityState
from app_runner.input_preparation.list_inputs import (
    list_input_states,
    print_input_states,
    FileState,
)

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


def get_inputs_and_print(
    inputs_yaml: Path,
    target_folder: Path | None,
    check: bool,
) -> list[FileState]:
    client = Bfabric.from_config()
    input_states = list_input_states(
        specs=InputsSpec.read_yaml(inputs_yaml),
        target_folder=target_folder or Path(""),
        client=client,
        check_files=check,
    )
    print_input_states(input_states)
    return input_states


@app_inputs.command(name="list")
def list_(
    inputs_yaml: Path,
    target_folder: Path | None = None,
    check: bool = False,
) -> None:
    """Lists the input files for an app.

    :param inputs_yaml: Path to the inputs.yml file.
    :param target_folder: Path to the target folder where the input files should be located, if different from the
        file containing the inputs.yml file.
    """
    setup_script_logging()
    get_inputs_and_print(inputs_yaml=inputs_yaml, target_folder=target_folder, check=check)


@app_inputs.command()
def check(
    inputs_yaml: Path,
    target_folder: Path | None = None,
) -> None:
    """Checks if the input files are present and have the correct content.

    The script will exit with a non-zero status
    code if any of the input files are missing or have incorrect content.
    :param inputs_yaml: Path to the inputs.yml file.
    :param target_folder: Path to the target folder where the input files should be located, if different from the
        file containing the inputs.yml file.
    """
    setup_script_logging()
    input_states = get_inputs_and_print(inputs_yaml=inputs_yaml, target_folder=target_folder, check=True)
    invalid_states = {state.integrity for state in input_states if state.integrity != IntegrityState.Correct}
    if invalid_states:
        print(f"Encountered invalid input states: {invalid_states}")
        raise SystemExit(1)
    else:
        print("All input files are correct.")

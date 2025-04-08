from pathlib import Path

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.inputs.prepare.prepare_folder import prepare_folder
from bfabric_app_runner.inputs.list_inputs.list_inputs import (
    list_input_states,
    print_input_states,
    FileState,
    IntegrityState,
)
from bfabric_app_runner.specs.inputs_spec import InputsSpec


@use_client
def cmd_inputs_prepare(
    inputs_yaml: Path,
    target_folder: Path | None = None,
    *,
    ssh_user: str | None = None,
    filter: str | None = None,
    client: Bfabric,
) -> None:
    """Prepare the input files by downloading and generating them (if necessary).

    :param inputs_yaml: Path to the inputs.yml file.
    :param target_folder: Path to the target folder where the input files should be downloaded.
    :param ssh_user: SSH user to use for downloading the input files, instead of the current user.
    :param filter: only this input file will be prepared.
    """
    prepare_folder(
        inputs_yaml=inputs_yaml,
        target_folder=target_folder,
        ssh_user=ssh_user,
        client=client,
        action="prepare",
        filter=filter,
    )


@use_client
def cmd_inputs_clean(
    inputs_yaml: Path,
    target_folder: Path | None = None,
    *,
    filter: str | None = None,
    client: Bfabric,
) -> None:
    """Removes all local copies of input files.

    :param inputs_yaml: Path to the inputs.yml file.
    :param target_folder: Path to the target folder where the input files should be removed.
    :param filter: only this input file will be removed.
    """
    # TODO clean shouldn't even need all these arguments, this could be refactored later
    prepare_folder(
        inputs_yaml=inputs_yaml,
        target_folder=target_folder,
        ssh_user=None,
        client=client,
        action="clean",
        filter=filter,
    )


def get_inputs_and_print(
    inputs_yaml: Path,
    target_folder: Path | None,
    check: bool,
    client: Bfabric,
) -> list[FileState]:
    """Reads the input files, performing integrity checks if requested, and prints the results."""
    input_states = list_input_states(
        specs=InputsSpec.read_yaml(inputs_yaml).inputs,
        target_folder=target_folder or Path(),
        client=client,
        check_files=check,
    )
    print_input_states(input_states)
    return input_states


@use_client
def cmd_inputs_list(
    inputs_yaml: Path,
    target_folder: Path | None = None,
    check: bool = False,
    *,
    client: Bfabric,
) -> None:
    """Lists the input files for an app.

    :param inputs_yaml: Path to the inputs.yml file.
    :param target_folder: Path to the target folder where the input files should be located, if different from the
        file containing the inputs.yml file.
    """
    get_inputs_and_print(inputs_yaml=inputs_yaml, target_folder=target_folder, check=check, client=client)


@use_client
def cmd_inputs_check(
    inputs_yaml: Path,
    target_folder: Path | None = None,
    *,
    client: Bfabric,
) -> None:
    """Checks if the input files are present and have the correct content.

    The script will exit with a non-zero status
    code if any of the input files are missing or have incorrect content.
    :param inputs_yaml: Path to the inputs.yml file.
    :param target_folder: Path to the target folder where the input files should be located, if different from the
        file containing the inputs.yml file.
    """
    input_states = get_inputs_and_print(inputs_yaml=inputs_yaml, target_folder=target_folder, check=True, client=client)
    invalid_states = {state.integrity for state in input_states if state.integrity != IntegrityState.Correct}
    if invalid_states:
        print(f"Encountered invalid input states: {invalid_states}")
        raise SystemExit(1)
    else:
        print("All input files are correct.")

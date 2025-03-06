from __future__ import annotations

from typing import TYPE_CHECKING, Literal, assert_never

from bfabric_app_runner.inputs.prepare.prepare_resolved_file import prepare_resolved_file
from bfabric_app_runner.inputs.prepare.prepare_resolved_static_file import prepare_resolved_static_file
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedInputs, ResolvedFile, ResolvedStaticFile
from bfabric_app_runner.inputs.resolve.resolver import Resolver
from bfabric_app_runner.specs.inputs_spec import (
    InputsSpec,
)
from loguru import logger

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric.bfabric import Bfabric


def prepare_folder(
    inputs_yaml: Path,
    target_folder: Path | None,
    client: Bfabric,
    ssh_user: str | None,
    filter: str | None,
    action: Literal["prepare", "clean"] = "prepare",
) -> None:
    """Prepares the input files of a chunk folder according to the provided specs.

    :param inputs_yaml: Path to the inputs.yml file.
    :param target_folder: Path to the target folder where the input files should be downloaded.
    :param client: Bfabric client to use for obtaining metadata about the input files.
    :param ssh_user: SSH user to use for downloading the input files, should it be different from the current user.
    :param filter: only this input file will be prepared.
    :param action: Action to perform.
    """
    # set defaults
    inputs_yaml = inputs_yaml.absolute()
    if target_folder is None:
        target_folder = inputs_yaml.parent

    # parse the specs
    inputs_spec = InputsSpec.read_yaml(inputs_yaml)

    # resolve the specs
    resolver = Resolver(client=client)
    input_files = resolver.resolve(specs=inputs_spec.inputs)

    # Note: In some cases, this will be very inefficient to do after resolving compared to doing it before, but in
    #       general not all filenames will be known upfront.
    if filter is not None:
        input_files = input_files.apply_filter(filter_files=[filter])
        if not input_files.files:
            raise ValueError(f"Filter {filter} did not match any input files")

    # prepare the folder
    if action == "prepare":
        _prepare_input_files(input_files=input_files, working_dir=target_folder, ssh_user=ssh_user)
    elif action == "clean":
        _clean_input_files(input_files=input_files, working_dir=target_folder)
    else:
        raise ValueError(f"Unknown action: {action}")


def _prepare_input_files(input_files: ResolvedInputs, working_dir: Path, ssh_user: str | None) -> None:
    """Prepares the input files in the working directory according to the provided specs."""
    for input_file in input_files.files:
        match input_file:
            case ResolvedFile():
                prepare_resolved_file(file=input_file, working_dir=working_dir, ssh_user=ssh_user)
            case ResolvedStaticFile():
                prepare_resolved_static_file(file=input_file, working_dir=working_dir)
            case _:
                assert_never(input_file)


def _clean_input_files(input_files: ResolvedInputs, working_dir: Path) -> None:
    """Removes the specified files from working_dir, if they exist."""
    for input_file in input_files.files:
        path = working_dir / input_file.filename
        if path.exists():
            path.unlink()
            logger.info(f"Removed {path}")

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bfabric_app_runner.inputs.list_inputs.integrity import check_integrity, IntegrityState
from bfabric_app_runner.inputs.resolve.resolver import Resolver
from rich.console import Console
from rich.table import Table, Column

if TYPE_CHECKING:
    from bfabric_app_runner.specs.inputs_spec import InputSpecType
    from pathlib import Path
    from bfabric.bfabric import Bfabric


@dataclass
class FileState:
    name: str
    path: Path
    exists: bool
    integrity: IntegrityState


def list_input_states(
    specs: list[InputSpecType],
    target_folder: Path,
    client: Bfabric,
    check_files: bool,
) -> list[FileState]:
    """Returns the states of the input files, performing integrity checks if requested.

    :param specs: List of input specs to consider
    :param target_folder: The target folder where the files should be stored
    :param client: A B-Fabric client
    :param check_files: If this is `True`, in addition to listing the files, their integrity states will be computed,
        otherwise the value is always `NotChecked`.
    """
    input_states = []
    resolver = Resolver(client=client)
    input_files = resolver.resolve(specs=specs)

    for input_file in input_files.files:
        path = target_folder / input_file.filename
        exists = path.exists()
        if not check_files:
            integrity = IntegrityState.NotChecked
        else:
            integrity = check_integrity(file=input_file, local_path=path, client=client)
        input_states.append(FileState(name=input_file.filename, path=path, exists=exists, integrity=integrity))
    return input_states


def print_input_states(input_states: list[FileState]) -> None:
    """Prints the states of the input files to the command line."""
    table = Table(
        Column("File"),
        Column("Exists"),
        Column("Integrity"),
    )
    for state in input_states:
        table.add_row(
            str(state.name),
            {True: "Yes", False: "No"}[state.exists],
            state.integrity.value,
        )
    console = Console()
    console.print(table)

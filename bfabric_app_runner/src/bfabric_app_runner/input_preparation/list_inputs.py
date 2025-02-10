from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console
from rich.table import Table, Column

from bfabric_app_runner.input_preparation.integrity import check_integrity, IntegrityState
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric_app_runner.specs.inputs_spec import InputSpecType
    from pathlib import Path
    from bfabric.bfabric import Bfabric


@dataclass
class FileState:
    name: str
    path: Path
    type: str
    exists: bool
    integrity: IntegrityState


def list_input_states(
    specs: list[InputSpecType],
    target_folder: Path,
    client: Bfabric,
    check_files: bool,
) -> list[FileState]:
    """Returns the states of the input files, performing integrity checks if requested."""
    input_states = []
    for spec in specs:
        filename = spec.resolve_filename(client=client)
        path = target_folder / filename
        exists = path.exists()
        if not check_files:
            integrity = IntegrityState.NotChecked
        else:
            integrity = check_integrity(spec=spec, local_path=path, client=client)
        input_states.append(FileState(name=filename, path=path, exists=exists, integrity=integrity, type=spec.type))
    return input_states


def print_input_states(input_states: list[FileState]) -> None:
    """Prints the states of the input files to the command line."""
    table = Table(
        Column("File"),
        Column("Input Type"),
        Column("Exists"),
        Column("Integrity"),
    )
    for state in input_states:
        table.add_row(
            str(state.name),
            str(state.type),
            {True: "Yes", False: "No"}[state.exists],
            state.integrity.value,
        )
    console = Console()
    console.print(table)

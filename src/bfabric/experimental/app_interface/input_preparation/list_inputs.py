from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.table import Table, Column

from bfabric.bfabric import Bfabric
from bfabric.experimental.app_interface.input_preparation._spec import InputSpecType
from bfabric.experimental.app_interface.input_preparation.integrity import check_integrity, IntegrityState


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

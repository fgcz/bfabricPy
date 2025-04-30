from pathlib import Path
from typing import assert_never

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.actions.types import (
    ActionDispatch,
    ActionInputs,
    ActionProcess,
    ActionOutputs,
    ActionRun,
    ActionGeneric,
)
from bfabric_app_runner.app_runner.runner import ChunksFile
from bfabric_app_runner.inputs.prepare.prepare_folder import prepare_folder


def execute(action: ActionGeneric) -> None:
    """Executes any action."""
    match action:
        case ActionDispatch():
            execute_dispatch(action)
        case ActionRun():
            execute_run(action)
        case ActionInputs():
            execute_inputs(action)
        case ActionProcess():
            execute_process(action)
        case ActionOutputs():
            execute_outputs(action)
        case _:
            assert_never(action)


def execute_dispatch(action: ActionDispatch) -> None:
    """Executes a dispatch action."""
    pass


def execute_run(action: ActionRun) -> None:
    """Executes a run action."""
    pass


@use_client
def execute_inputs(action: ActionInputs, *, client: Bfabric) -> None:
    """Executes an inputs action."""
    chunk_paths = _validate_chunks_list(action.work_dir, action.chunk)
    for chunk_path in chunk_paths:
        prepare_folder(
            inputs_yaml=chunk_path / "inputs.yml",
            target_folder=chunk_path,
            client=client,
            ssh_user=action.ssh_user,
            filter=action.filter,
            action="prepare",
        )


def execute_process(action: ActionProcess) -> None:
    """Executes a process action."""
    pass


def execute_outputs(action: ActionOutputs) -> None:
    """Executes an outputs action."""
    pass


def _validate_chunks_list(work_dir: Path, chunk: str | None) -> list[Path]:
    """Converts the chunk argument to a list of Path objects.

    If it is None, all chunks from the chunks.yml file are returned.
    If it is specified, it is converted to a list with one element.
    All paths will be resolved to the work_dir.
    """
    if chunk is None:
        return [work_dir / p for p in ChunksFile.read(work_dir=work_dir).chunks]
    else:
        return [work_dir / chunk]

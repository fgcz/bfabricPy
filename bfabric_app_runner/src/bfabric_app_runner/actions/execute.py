from pathlib import Path
from typing import assert_never

from bfabric import Bfabric
from bfabric.experimental.workunit_definition import WorkunitDefinition
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
from bfabric_app_runner.output_registration.register import register_all
from bfabric_app_runner.specs.outputs_spec import OutputsSpec


def execute(action: ActionGeneric, client: Bfabric) -> None:
    """Executes any action."""
    match action:
        case ActionDispatch():
            execute_dispatch(action=action, client=client)
        case ActionRun():
            execute_run(action=action, client=client)
        case ActionInputs():
            execute_inputs(action=action, client=client)
        case ActionProcess():
            execute_process(action=action, client=client)
        case ActionOutputs():
            execute_outputs(action=action, client=client)
        case _:
            assert_never(action)


def execute_dispatch(action: ActionDispatch, client: Bfabric) -> None:
    """Executes a dispatch action."""
    pass


def execute_run(action: ActionRun, client: Bfabric) -> None:
    """Executes a run action."""
    pass


def execute_inputs(action: ActionInputs, client: Bfabric) -> None:
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


def execute_process(action: ActionProcess, client: Bfabric) -> None:
    """Executes a process action."""
    pass


def execute_outputs(action: ActionOutputs, client: Bfabric) -> None:
    """Executes an outputs action."""
    chunk_paths = _validate_chunks_list(action.work_dir, action.chunk)
    for chunk_path in chunk_paths:
        specs_list = OutputsSpec.read_yaml(chunk_path / "outputs.yml")
        register_all(
            client=client,
            # TODO (cache etc)
            workunit_definition=WorkunitDefinition.from_ref(workunit=action.workunit_ref, client=client),
            specs_list=specs_list,
            ssh_user=action.ssh_user,
            # TODO
            # reuse_default_resource=reuse_default_resource,
            reuse_default_resource=True,
            force_storage=action.force_storage,
        )


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

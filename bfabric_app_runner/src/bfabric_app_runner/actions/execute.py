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
from bfabric_app_runner.cli.app import cmd_app_dispatch
from bfabric_app_runner.cli.chunk import cmd_chunk_process, cmd_chunk_outputs
from bfabric_app_runner.inputs.prepare.prepare_folder import prepare_folder


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
    cmd_app_dispatch(
        app_spec=action.app_ref,
        work_dir=action.work_dir,
        workunit_ref=action.workunit_ref,
        create_makefile=False,
        client=client,
    )

    if not action.read_only:
        # Set the workunit status to processing
        workunit_definition = WorkunitDefinition.from_yaml(action.work_dir / "workunit_definition.yml")
        client.save("workunit", {"id": workunit_definition.registration.workunit_id, "status": "processing"})


def execute_run(action: ActionRun, client: Bfabric) -> None:
    """Executes a run action."""
    chunks = _validate_chunks_list(action.work_dir, action.chunk)
    for chunk in chunks:
        execute_inputs(action=ActionInputs.from_action_run(action, chunk=str(chunk)), client=client)
        execute_process(action=ActionProcess.from_action_run(action, chunk=str(chunk)), client=client)
        execute_outputs(action=ActionOutputs.from_action_run(action, chunk=str(chunk)), client=client)


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
    chunk_paths = _validate_chunks_list(action.work_dir, action.chunk)

    # TODO to be cleaned later
    for chunk in chunk_paths:
        cmd_chunk_process(app_spec=action.app_ref, chunk_dir=chunk, client=client)


def execute_outputs(action: ActionOutputs, client: Bfabric) -> None:
    """Executes an outputs action."""
    chunk_paths = _validate_chunks_list(action.work_dir, action.chunk)

    # TODO to bo cleaned later
    for chunk_path in chunk_paths:
        # this includes the legacy collect step
        cmd_chunk_outputs(
            app_spec=action.app_ref,
            chunk_dir=chunk_path,
            workunit_ref=action.workunit_ref,
            ssh_user=action.ssh_user,
            force_storage=action.force_storage,
            read_only=action.read_only,
            # TODO
            # reuse_default_resource=action.reuse_default_resource,
            reuse_default_resource=True,
            client=client,
        )


def _validate_chunks_list(work_dir: Path, chunk: str | None) -> list[Path]:
    """Converts the chunk argument to a list of Path objects.

    If it is None, all chunks from the chunks.yml file are returned.
    If it is specified, it is converted to a list with one element.
    All paths will be resolved to the work_dir and into absolute paths.
    """
    work_dir = work_dir.resolve()
    if chunk is None:
        return [work_dir / p for p in ChunksFile.read(work_dir=work_dir).chunks]
    else:
        return [work_dir / chunk]

from pathlib import Path
from typing import assert_never

from bfabric import Bfabric
from bfabric.experimental.entity_lookup_cache import EntityLookupCache
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric_app_runner.actions.types import (
    ActionDispatch,
    ActionInputs,
    ActionProcess,
    ActionOutputs,
    ActionRun,
    ActionGeneric,
)
from bfabric_app_runner.app_runner.resolve_app import load_workunit_information
from bfabric_app_runner.app_runner.runner import ChunksFile, Runner
from bfabric_app_runner.cli.app import cmd_app_dispatch
from bfabric_app_runner.inputs.prepare.prepare_folder import prepare_folder
from bfabric_app_runner.output_registration import register_outputs


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
    chunk_dirs = _validate_chunks_list(action.work_dir, action.chunk)
    for chunk_dir_rel in chunk_dirs:
        execute_inputs(action=ActionInputs.from_action_run(action, chunk=str(chunk_dir_rel)), client=client)
        execute_process(action=ActionProcess.from_action_run(action, chunk=str(chunk_dir_rel)), client=client)
        execute_outputs(action=ActionOutputs.from_action_run(action, chunk=str(chunk_dir_rel)), client=client)


def execute_inputs(action: ActionInputs, client: Bfabric) -> None:
    """Executes an inputs action."""
    chunk_dirs = _validate_chunks_list(action.work_dir, action.chunk)
    for chunk_dir_rel in chunk_dirs:
        prepare_folder(
            inputs_yaml=chunk_dir_rel / "inputs.yml",
            target_folder=chunk_dir_rel,
            client=client,
            ssh_user=action.ssh_user,
            filter=action.filter,
            action="prepare",
        )


def execute_process(action: ActionProcess, client: Bfabric) -> None:
    """Executes a process action."""
    chunk_dirs = _validate_chunks_list(action.work_dir, action.chunk)

    # TODO to be cleaned later
    for chunk_dir_rel in chunk_dirs:
        app_spec = action.app_ref
        chunk_dir = chunk_dir_rel.resolve()
        # TODO we should enforce that chunks are subdirectories of the work_dir when they are created
        app_version, _, workunit_ref = load_workunit_information(
            app_spec=app_spec,
            client=client,
            work_dir=chunk_dir / "..",
            workunit_ref=chunk_dir / ".." / "workunit_definition.yml",
        )

        with EntityLookupCache.enable():
            runner = Runner(spec=app_version, client=client, ssh_user=None)
            runner.run_process(chunk_dir=chunk_dir)


def execute_outputs(action: ActionOutputs, client: Bfabric) -> None:
    """Executes an outputs action."""
    chunk_dirs = _validate_chunks_list(action.work_dir, action.chunk)

    # TODO to bo cleaned later
    for chunk_dir_rel in chunk_dirs:
        # this includes the legacy collect step
        # TODO redundant functionality with "outputs register"
        chunk_dir = chunk_dir_rel.resolve()
        app_version, _, workunit_ref = load_workunit_information(
            app_spec=action.app_ref, client=client, work_dir=chunk_dir, workunit_ref=action.workunit_ref
        )
        runner = Runner(spec=app_version, client=client, ssh_user=action.ssh_user)
        runner.run_collect(workunit_ref=action.workunit_ref, chunk_dir=chunk_dir)
        # TODO see above, chunk_dir being a direct subdirectory of the work_dir is not enforced yet but should be
        workunit_definition = WorkunitDefinition.from_yaml(path=chunk_dir / ".." / "workunit_definition.yml")
        if not action.read_only:
            register_outputs(
                outputs_yaml=chunk_dir / "outputs.yml",
                workunit_definition=workunit_definition,
                client=client,
                ssh_user=action.ssh_user,
                force_storage=action.force_storage,
                reuse_default_resource=True,
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

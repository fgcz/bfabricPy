from pathlib import Path
from typing import assert_never, Any

from loguru import logger

from bfabric import Bfabric
from bfabric.entities import WorkflowTemplateStep, WorkflowTemplate, WorkflowStep
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
from bfabric_app_runner.app_runner.runner import ChunksFile
from bfabric_app_runner.app_runner.runner import Runner
from bfabric_app_runner.inputs.prepare.prepare_folder import prepare_folder
from bfabric_app_runner.output_registration import register_outputs


def execute(action: ActionGeneric, client: Bfabric) -> None:
    """Executes the provided action."""
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
    app_version, bfabric_app_spec, workunit_ref = load_workunit_information(
        app_spec=action.app_ref, client=client, work_dir=action.work_dir, workunit_ref=action.workunit_ref
    )

    with EntityLookupCache.enable():
        runner = Runner(spec=app_version, client=client, ssh_user=None)
        runner.run_dispatch(workunit_ref=workunit_ref, work_dir=action.work_dir)

    if not action.read_only:
        # Set the workunit status to processing
        workunit_definition = WorkunitDefinition.from_yaml(workunit_ref)
        client.save("workunit", {"id": workunit_definition.registration.workunit_id, "status": "processing"})

        # Create a workflowstep template if specified
        if bfabric_app_spec.workflow_template_step_id:
            logger.info(f"Creating workflowstep from template {bfabric_app_spec.workflow_template_step_id}")
            _register_workflow_step(
                workflow_template_step_id=bfabric_app_spec.workflow_template_step_id,
                workunit_definition=workunit_definition,
                client=client,
            )


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

    for chunk_dir_rel in chunk_dirs:
        app_spec = action.app_ref
        chunk_dir = chunk_dir_rel.resolve()
        app_version, _, workunit_ref = load_workunit_information(
            app_spec=app_spec,
            client=client,
            work_dir=action.work_dir,
            workunit_ref=action.work_dir / "workunit_definition.yml",
        )

        with EntityLookupCache.enable():
            runner = Runner(spec=app_version, client=client, ssh_user=None)
            runner.run_process(chunk_dir=chunk_dir)


def execute_outputs(action: ActionOutputs, client: Bfabric) -> None:
    """Executes an outputs action."""
    chunk_dirs = _validate_chunks_list(action.work_dir, action.chunk)

    for chunk_dir_rel in chunk_dirs:
        # this includes the legacy collect step
        chunk_dir = chunk_dir_rel.resolve()
        app_version, _, workunit_ref = load_workunit_information(
            app_spec=action.app_ref, client=client, work_dir=chunk_dir, workunit_ref=action.workunit_ref
        )
        runner = Runner(spec=app_version, client=client, ssh_user=action.ssh_user)
        runner.run_collect(workunit_ref=action.workunit_ref, chunk_dir=chunk_dir)
        workunit_definition = WorkunitDefinition.from_yaml(path=action.work_dir / "workunit_definition.yml")
        if not action.read_only:
            register_outputs(
                outputs_yaml=chunk_dir / "outputs.yml",
                workunit_definition=workunit_definition,
                client=client,
                ssh_user=action.ssh_user,
                force_storage=action.force_storage,
                reuse_default_resource=True,
            )


def _register_workflow_step(
    workflow_template_step_id: int, workunit_definition: WorkunitDefinition, client: Bfabric
) -> None:
    # Load the workflow template step
    workflow_template_step = WorkflowTemplateStep.find(id=workflow_template_step_id, client=client)
    if not workflow_template_step:
        logger.error(f"Misconfigured {workflow_template_step_id=}, cannot find it in the database.")
        return

    # Find or create the workflow entity
    workflow = _find_or_create_workflow(
        workflow_template=workflow_template_step.workflow_template,
        workunit_definition=workunit_definition,
        client=client,
    )

    # Prepare the data for the workflow step
    workunit_id = workunit_definition.registration.workunit_id
    workflow_step_data = {
        "workflowid": workflow["id"],
        "workflowtemplatestepid": workflow_template_step.id,
        "supervisorid": workunit_definition.registration.user_id,
        "workunitid": workunit_id,
    }
    if workunit_definition.execution.dataset is not None:
        workflow_step_data["datasetid"] = workunit_definition.execution.dataset

    # Find or create the workflow step entity
    _create_workflow_step_if_not_exists(
        workflow=workflow, workflow_step_data=workflow_step_data, workunit_id=workunit_id, client=client
    )


def _create_workflow_step_if_not_exists(
    workflow: dict[str, Any], workflow_step_data: dict[str, Any], workunit_id: int, client: Bfabric
) -> None:
    workflow_step = WorkflowStep.find_by(workflow_step_data, client=client)
    if workflow_step:
        logger.info(f"Workflow step already exists: {workflow_step}, skipping creation.")
        return
    resp = client.save("workflowstep", workflow_step_data)
    logger.info(f"Created workflow step: {resp[0]['id']} for workunit {workunit_id} in workflow {workflow['id']}.")


def _find_or_create_workflow(
    workflow_template: WorkflowTemplate, workunit_definition: WorkunitDefinition, client: Bfabric
) -> dict[str, Any]:
    container_id = workunit_definition.registration.container_id
    workflow_data = {"containerid": container_id, "workflowtemplateid": workflow_template.id}
    resp = client.read("workflow", workflow_data)
    if len(resp) > 0:
        workflow = resp[0]
    else:
        resp = client.save("workflow", workflow_data)
        workflow = resp[0]
    return workflow


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

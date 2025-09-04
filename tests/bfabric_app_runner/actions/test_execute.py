from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from bfabric_app_runner.actions.execute import execute_run, execute_outputs, _register_workflow_step
from bfabric_app_runner.actions.types import ActionRun, ActionInputs, ActionProcess, ActionOutputs


@pytest.fixture
def action_run() -> ActionRun:
    """Fixture for ActionRun."""
    return ActionRun(
        work_dir=Path("/test/work_dir"),
        chunk=None,
        ssh_user="ssh_user",
        filter="filter",
        app_ref=Path("app_ref"),
        force_storage=Path("force_storage"),
        workunit_ref=Path("workunit_ref"),
    )


@pytest.fixture
def mock_client(mocker: MockerFixture):
    return mocker.Mock(name="mock_client")


def test_run(mocker, action_run, mock_client):
    mock_validate_chunks_list = mocker.patch(
        "bfabric_app_runner.actions.execute._validate_chunks_list", return_value=[Path("chunk1")]
    )
    mock_execute_inputs = mocker.patch("bfabric_app_runner.actions.execute.execute_inputs")
    mock_execute_process = mocker.patch("bfabric_app_runner.actions.execute.execute_process")
    mock_execute_outputs = mocker.patch("bfabric_app_runner.actions.execute.execute_outputs")

    execute_run(action=action_run, client=mock_client)

    mock_execute_inputs.assert_called_once_with(
        action=ActionInputs(
            work_dir=Path("/test/work_dir"),
            chunk="chunk1",
            ssh_user="ssh_user",
            filter="filter",
        ),
        client=mock_client,
    )
    mock_execute_process.assert_called_once_with(
        action=ActionProcess(
            work_dir=Path("/test/work_dir"),
            chunk="chunk1",
            app_ref=Path("app_ref"),
        ),
        client=mock_client,
    )
    mock_execute_outputs.assert_called_once_with(
        action=ActionOutputs(
            work_dir=Path("/test/work_dir"),
            chunk="chunk1",
            workunit_ref=Path("workunit_ref"),
            app_ref=Path("app_ref"),
            ssh_user="ssh_user",
            force_storage=Path("force_storage"),
        ),
        client=mock_client,
    )


@pytest.fixture
def mock_workunit_definition(mocker):
    mock_def = mocker.Mock()
    mock_def.execution.dataset = 9999
    mock_def.registration = mocker.Mock(workunit_id=123, container_id=456, user_id=555)
    return mock_def


def test_execute_outputs_calls_register_workflow_step_when_template_exists(mocker, mock_client):
    """Test that execute_outputs calls _register_workflow_step when workflow_template_step_id exists."""
    # Setup
    work_dir = Path("/tmp/work")
    chunk_dir = work_dir / "chunk1"

    # Mock dependencies
    mock_validate_chunks_list = mocker.patch(
        "bfabric_app_runner.actions.execute._validate_chunks_list", return_value=[Path("chunk1")]
    )
    mock_load_workunit_info = mocker.patch("bfabric_app_runner.actions.execute.load_workunit_information")
    mock_app_spec = mocker.Mock()
    mock_app_spec.workflow_template_step_id = 789
    mock_load_workunit_info.return_value = (mocker.Mock(), mock_app_spec, mocker.Mock())

    mock_runner = mocker.patch("bfabric_app_runner.actions.execute.Runner")
    mock_workunit_def = mocker.patch("bfabric_app_runner.actions.execute.WorkunitDefinition.from_yaml").return_value
    mock_register_workflow = mocker.patch("bfabric_app_runner.actions.execute._register_workflow_step")
    mocker.patch("bfabric_app_runner.actions.execute.register_outputs")

    # Create action
    action = ActionOutputs(
        work_dir=work_dir,
        chunk="chunk1",
        workunit_ref=Path("workunit_ref"),
        app_ref=Path("app_ref"),
        ssh_user="ssh_user",
        force_storage=None,
        read_only=False,
    )

    # Execute
    execute_outputs(action, mock_client)

    # Verify _register_workflow_step was called
    mock_register_workflow.assert_called_once_with(
        workflow_template_step_id=789, workunit_definition=mock_workunit_def, client=mock_client
    )


def test_execute_outputs_does_not_call_register_workflow_step_when_read_only(mocker, mock_client):
    """Test that execute_outputs does not call _register_workflow_step when read_only=True."""
    # Setup
    work_dir = Path("/tmp/work")

    # Mock dependencies
    mock_validate_chunks_list = mocker.patch(
        "bfabric_app_runner.actions.execute._validate_chunks_list", return_value=[Path("chunk1")]
    )
    mock_load_workunit_info = mocker.patch("bfabric_app_runner.actions.execute.load_workunit_information")
    mock_app_spec = mocker.Mock()
    mock_app_spec.workflow_template_step_id = 789
    mock_load_workunit_info.return_value = (mocker.Mock(), mock_app_spec, mocker.Mock())

    mock_runner = mocker.patch("bfabric_app_runner.actions.execute.Runner")
    mocker.patch("bfabric_app_runner.actions.execute.WorkunitDefinition.from_yaml")
    mock_register_workflow = mocker.patch("bfabric_app_runner.actions.execute._register_workflow_step")
    mocker.patch("bfabric_app_runner.actions.execute.register_outputs")

    # Create action with read_only=True
    action = ActionOutputs(
        work_dir=work_dir,
        chunk="chunk1",
        workunit_ref=Path("workunit_ref"),
        app_ref=Path("app_ref"),
        ssh_user="ssh_user",
        force_storage=None,
        read_only=True,
    )

    # Execute
    execute_outputs(action, mock_client)

    # Verify _register_workflow_step was NOT called
    mock_register_workflow.assert_not_called()


def test_register_workflow_step_creates_workflow_and_step(mocker, mock_client, mock_workunit_definition):
    """Test _register_workflow_step function creates workflow and step entities."""
    # Mock entities using the new bfabric.entities API
    mock_workflow_template = mocker.Mock(id=999)
    mock_workflow_template_step = mocker.Mock(id=789, workflow_template=mock_workflow_template)

    # Mock WorkflowTemplateStep.find
    mock_wts_find = mocker.patch("bfabric_app_runner.actions.execute.WorkflowTemplateStep.find")
    mock_wts_find.return_value = mock_workflow_template_step

    # Mock WorkflowStep.find_by to return None (not found, so will create)
    mock_ws_find_by = mocker.patch("bfabric_app_runner.actions.execute.WorkflowStep.find_by")
    mock_ws_find_by.return_value = None

    # Setup client mock responses for workflow lookup and creation
    mock_client.read.side_effect = [
        [],  # workflow read (not found, so will create)
    ]
    mock_client.save.side_effect = [
        [{"id": 100}],  # created workflow
        [{"id": 200}],  # created workflowstep
    ]

    # Execute
    _register_workflow_step(789, mock_workunit_definition, mock_client)

    # Verify entity method calls
    expected_workflowstep = {
        "workflowid": 100,
        "workflowtemplatestepid": 789,
        "supervisorid": 555,
        "workunitid": 123,
        "datasetid": 9999,
    }
    mock_wts_find.assert_called_once_with(id=789, client=mock_client)
    mock_ws_find_by.assert_called_once_with(expected_workflowstep, client=mock_client)

    # Verify client calls for workflow creation
    mock_client.read.assert_called_once_with("workflow", {"containerid": 456, "workflowtemplateid": 999})

    expected_save_calls = [
        mocker.call("workflow", {"containerid": 456, "workflowtemplateid": 999}),
        mocker.call("workflowstep", expected_workflowstep),
    ]
    mock_client.save.assert_has_calls(expected_save_calls)

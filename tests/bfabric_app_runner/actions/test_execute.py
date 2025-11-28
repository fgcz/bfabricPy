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
def action_outputs() -> ActionOutputs:
    """Fixture for ActionOutputs."""
    return ActionOutputs(
        work_dir=Path("/test/work_dir"),
        chunk="chunk1",
        workunit_ref=Path("workunit_ref"),
        app_ref=Path("app_ref"),
        ssh_user="ssh_user",
        force_storage=None,
        read_only=False,
    )


@pytest.fixture
def mock_workunit_definition(mocker):
    mock_def = mocker.Mock()
    mock_def.execution.dataset = 9999
    mock_def.registration = mocker.Mock(workunit_id=123, container_id=456, user_id=555)
    return mock_def


@pytest.fixture
def mock_app_spec_with_workflow_template(mocker):
    """App spec with workflow_template_step_id set."""
    mock_app_spec = mocker.Mock()
    mock_app_spec.workflow_template_step_id = 789
    return mock_app_spec


@pytest.fixture
def mock_app_spec_without_workflow_template(mocker):
    """App spec with workflow_template_step_id set to None."""
    mock_app_spec = mocker.Mock()
    mock_app_spec.workflow_template_step_id = None
    return mock_app_spec


@pytest.fixture
def execute_outputs_common_mocks(mocker, mock_workunit_definition):
    """Common mocks needed for execute_outputs tests."""
    mocks = {
        "validate_chunks_list": mocker.patch(
            "bfabric_app_runner.actions.execute._validate_chunks_list", return_value=[Path("chunk1")]
        ),
        "load_workunit_info": mocker.patch("bfabric_app_runner.actions.execute.load_workunit_information"),
        "runner": mocker.patch("bfabric_app_runner.actions.execute.Runner"),
        "workunit_definition_from_yaml": mocker.patch(
            "bfabric_app_runner.actions.execute.WorkunitDefinition.from_yaml", return_value=mock_workunit_definition
        ),
        "register_workflow_step": mocker.patch("bfabric_app_runner.actions.execute._register_workflow_step"),
        "register_outputs": mocker.patch("bfabric_app_runner.actions.execute.register_outputs"),
    }
    return mocks


def test_execute_outputs_calls_register_workflow_step_when_template_exists(
    action_outputs,
    mock_client,
    execute_outputs_common_mocks,
    mock_app_spec_with_workflow_template,
    mock_workunit_definition,
):
    """Test that execute_outputs calls _register_workflow_step when workflow_template_step_id exists."""
    # Setup load_workunit_info to return our app spec with workflow template
    execute_outputs_common_mocks["load_workunit_info"].return_value = (
        mock_client,
        mock_app_spec_with_workflow_template,
        mock_client,
    )

    # Execute
    execute_outputs(action_outputs, mock_client)

    # Verify _register_workflow_step was called
    execute_outputs_common_mocks["register_workflow_step"].assert_called_once_with(
        workflow_template_step_id=789, workunit_definition=mock_workunit_definition, client=mock_client
    )


def test_execute_outputs_does_not_call_register_workflow_step_when_read_only(
    action_outputs, mock_client, execute_outputs_common_mocks, mock_app_spec_with_workflow_template
):
    """Test that execute_outputs does not call _register_workflow_step when read_only=True."""
    # Setup read_only action and load_workunit_info to return our app spec with workflow template
    action_outputs.read_only = True
    execute_outputs_common_mocks["load_workunit_info"].return_value = (
        mock_client,
        mock_app_spec_with_workflow_template,
        mock_client,
    )

    # Execute
    execute_outputs(action_outputs, mock_client)

    # Verify _register_workflow_step was NOT called
    execute_outputs_common_mocks["register_workflow_step"].assert_not_called()


def test_execute_outputs_logs_warning_when_read_only(action_outputs, mock_client, mocker):
    """Test that execute_outputs logs warning messages when read_only=True."""
    # Setup read_only action
    action_outputs.read_only = True

    # Mock logger.warning to capture log messages
    mock_logger_warning = mocker.patch("bfabric_app_runner.actions.execute.logger.warning")

    # Execute
    execute_outputs(action_outputs, mock_client)

    # Verify warning messages were logged
    expected_calls = [
        mocker.call("Read-only mode: Skipping output registration and staging."),
        mocker.call("To actually stage results, remove the --read-only flag from your configuration."),
    ]
    mock_logger_warning.assert_has_calls(expected_calls)


def test_execute_outputs_does_not_call_register_workflow_step_when_no_template(
    action_outputs, mock_client, execute_outputs_common_mocks, mock_app_spec_without_workflow_template
):
    """Test that execute_outputs does not call _register_workflow_step when workflow_template_step_id is None."""
    # Setup load_workunit_info to return our app spec without workflow template
    execute_outputs_common_mocks["load_workunit_info"].return_value = (
        mock_client,
        mock_app_spec_without_workflow_template,
        mock_client,
    )

    # Execute
    execute_outputs(action_outputs, mock_client)

    # Verify _register_workflow_step was NOT called
    execute_outputs_common_mocks["register_workflow_step"].assert_not_called()


def test_register_workflow_step_creates_workflow_and_step(mocker, mock_client, mock_workunit_definition):
    """Test _register_workflow_step function creates workflow and step entities."""
    # Mock entities using the new bfabric.entities API
    mock_workflow_template = mocker.Mock(id=999)
    mock_workflow_template_step = mocker.Mock(id=789, workflow_template=mock_workflow_template)

    # Mock WorkflowTemplateStep.find
    mock_wts_find = mocker.patch("bfabric_app_runner.actions.execute.Workflowtemplatestep.find")
    mock_wts_find.return_value = mock_workflow_template_step

    # Mock WorkflowStep.find_by to return None (not found, so will create)
    mock_ws_find_by = mocker.patch("bfabric_app_runner.actions.execute.Workflowstep.find_by")
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

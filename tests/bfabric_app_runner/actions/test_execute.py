from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from bfabric_app_runner.actions.execute import execute_run
from bfabric_app_runner.actions.types import ActionRun, ActionInputs, ActionProcess, ActionOutputs


@pytest.fixture
def action_run() -> ActionRun:
    """Fixture for ActionRun."""
    return ActionRun(
        work_dir=Path("/test/work_dir"),
        chunk=None,
        ssh_user="ssh_user",
        filter="filter",
        app_ref="app_ref",
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
            app_ref="app_ref",
        ),
        client=mock_client,
    )
    mock_execute_outputs.assert_called_once_with(
        action=ActionOutputs(
            work_dir=Path("/test/work_dir"),
            chunk="chunk1",
            workunit_ref=Path("workunit_ref"),
            app_ref="app_ref",
            ssh_user="ssh_user",
            force_storage=Path("force_storage"),
        ),
        client=mock_client,
    )

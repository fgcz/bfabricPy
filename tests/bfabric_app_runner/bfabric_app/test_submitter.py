import base64
from pathlib import Path
from typing import Any

import pytest
import yaml
from pytest_mock import MockerFixture

from bfabric import Bfabric
from bfabric.entities import Executable
from bfabric.entities import Workunit, ExternalJob
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric_app_runner.bfabric_app.submitter import Submitter
from bfabric_app_runner.bfabric_app.workunit_wrapper_data import WorkunitWrapperData
from bfabric_app_runner.specs.app.app_version import AppVersion
from bfabric_app_runner.specs.submitters_spec import SubmittersSpecTemplate, SubmitterSlurmSpec
from bfabric_app_runner.submitter.slurm_submitter import SlurmSubmitter
from tests.conftest import yaml_fixture

WORKUNIT_ID = 500


@pytest.fixture
def mock_client(mocker: MockerFixture) -> Bfabric:
    return mocker.MagicMock()


@pytest.fixture
def mock_workunit(mocker: MockerFixture) -> Workunit:
    return mocker.MagicMock(id=WORKUNIT_ID)


@pytest.fixture
def mock_external_job(mocker: MockerFixture, mock_workunit: Workunit) -> ExternalJob:
    return mocker.MagicMock(workunit=mock_workunit)


@pytest.fixture
def mock_submitters_spec_template(mock_submitter_slurm_spec) -> SubmittersSpecTemplate:
    return SubmittersSpecTemplate(submitters={"test_submitter": mock_submitter_slurm_spec})


@pytest.fixture
def mock_submitter(
    mock_client: Bfabric, mock_external_job: ExternalJob, mock_submitters_spec_template: SubmittersSpecTemplate
) -> Submitter:
    return Submitter(
        client=mock_client, external_job=mock_external_job, submitters_spec_template=mock_submitters_spec_template
    )


mock_app_version = yaml_fixture(AppVersion, "app_version")
mock_workunit_definition = yaml_fixture(WorkunitDefinition, "workunit_definition")
mock_submitter_slurm_spec = yaml_fixture(SubmitterSlurmSpec, "submitter_slurm_spec")


@pytest.fixture
def mock_workunit_wrapper_data(
    mock_app_version: AppVersion, mock_workunit_definition: WorkunitDefinition
) -> WorkunitWrapperData:
    return WorkunitWrapperData(
        workunit_definition=mock_workunit_definition, app_version=mock_app_version, app_runner_version="1.0.0"
    )


@pytest.fixture
def mock_executable_data(mock_workunit_wrapper_data: WorkunitWrapperData) -> dict[str, Any]:
    yaml_str = yaml.safe_dump(mock_workunit_wrapper_data.model_dump(mode="json"))
    base64_str = base64.b64encode(yaml_str.encode()).decode()
    return {"1": {"context": "WORKUNIT", "base64": base64_str}}


def test_get_workunit_wrapper_data(
    mocker: MockerFixture, mock_submitter: Submitter, mock_client: Bfabric, mock_executable_data: dict[str, Any]
) -> None:
    # Setup
    mock_executable_find_by = mocker.patch.object(Executable, "find_by", return_value=mock_executable_data)

    # Execute
    result = mock_submitter.get_workunit_wrapper_data()

    # Verify
    assert isinstance(result, WorkunitWrapperData)
    assert result.app_version.version == "1.0.0"
    assert result.app_version.submitter.name == "test_submitter"
    mock_executable_find_by.assert_called_once_with({"workunitid": WORKUNIT_ID}, client=mock_client)


def test_get_workunit_wrapper_data_no_executable(
    mocker: MockerFixture, mock_submitter: Submitter, mock_client: Bfabric
) -> None:
    # Setup
    mock_executable_find_by = mocker.patch.object(Executable, "find_by", return_value={})

    # Execute and verify
    with pytest.raises(ValueError, match="Expected exactly one WORKUNIT executable"):
        mock_submitter.get_workunit_wrapper_data()

    mock_executable_find_by.assert_called_once_with({"workunitid": WORKUNIT_ID}, client=mock_client)


def test_get_submitter_spec(
    mock_submitter: Submitter,
    mock_submitters_spec_template: SubmittersSpecTemplate,
    mock_workunit_wrapper_data: WorkunitWrapperData,
) -> None:
    # Execute
    result = mock_submitter.get_submitter_spec(mock_workunit_wrapper_data)

    # Verify
    assert isinstance(result, SubmitterSlurmSpec)
    assert result.params["--partition"] == "compute"
    assert result.config.worker_scratch_dir == Path("/test/worker-scratch-dir/-1_Testing_App/-1")


def test_get_submitter_spec_not_found(
    mock_submitter: Submitter,
    mock_submitters_spec_template: SubmittersSpecTemplate,
    mock_workunit_wrapper_data: WorkunitWrapperData,
) -> None:
    # Setup
    mock_workunit_wrapper_data.app_version.submitter.name = "nonexistent_submitter"

    # Execute and verify
    with pytest.raises(ValueError, match="Submitter 'nonexistent_submitter' not found"):
        mock_submitter.get_submitter_spec(mock_workunit_wrapper_data)


def test_run(
    mocker: MockerFixture,
    mock_submitter: Submitter,
    mock_client: Bfabric,
    mock_workunit_wrapper_data: WorkunitWrapperData,
    mock_executable_data: dict[str, Any],
    mock_submitters_spec_template: SubmittersSpecTemplate,
) -> None:
    # Setup
    mocker.patch.object(Executable, "find_by", return_value=mock_executable_data)
    mock_slurm_submitter = mocker.MagicMock(spec=SlurmSubmitter)
    mocker.patch("bfabric_app_runner.bfabric_app.submitter.SlurmSubmitter", return_value=mock_slurm_submitter)

    # Execute
    mock_submitter.run()

    # Verify
    mock_slurm_submitter.submit.assert_called_once_with(workunit_wrapper_data=mock_workunit_wrapper_data)
    mock_slurm_submitter.create_log_resource.assert_called_once_with(
        workunit_wrapper_data=mock_workunit_wrapper_data, client=mock_client
    )

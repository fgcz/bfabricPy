from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel

from bfabric_app_runner.app_runner.runner import Runner, run_app


# Mock classes to represent dependencies
class MockCommand(BaseModel):
    def to_shell(self) -> list[str]:
        return ["mock-command"]


class MockCommands(BaseModel):
    dispatch: MockCommand = MockCommand()
    process: MockCommand = MockCommand()
    collect: MockCommand = MockCommand()


class MockAppVersion(BaseModel):
    commands: MockCommands = MockCommands()
    reuse_default_resource: bool = False


@pytest.fixture
def mock_app_version():
    """Fixture providing a mock app specification"""
    return MockAppVersion()


@pytest.fixture
def mock_bfabric(mocker):
    """Fixture providing a mock bfabric client"""
    return mocker.Mock(save=mocker.Mock())


@pytest.fixture
def mock_workunit_definition():
    """Fixture providing a mock workunit definition"""

    class MockRegistration:
        workunit_id = 123

    class MockWorkunitDefinition:
        registration = MockRegistration()

    return MockWorkunitDefinition()


@pytest.fixture
def setup_work_dir(tmp_path):
    """Fixture setting up a temporary work directory with required files"""
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # Create chunks.yml
    chunks_dir = work_dir / "chunk1"
    chunks_dir.mkdir()
    chunks_yaml = {"chunks": [str(chunks_dir)]}
    (work_dir / "chunks.yml").write_text(yaml.dump(chunks_yaml))

    # Create required files in chunk directory
    (chunks_dir / "inputs.yml").touch()
    (chunks_dir / "outputs.yml").touch()

    return work_dir


def test_runner_initialization(mock_app_version, mock_bfabric):
    """Test Runner initialization"""
    runner = Runner(spec=mock_app_version, client=mock_bfabric, ssh_user="test_user")
    print(runner)
    print(runner.__dict__)
    assert runner._app_version == mock_app_version
    assert runner._client == mock_bfabric
    assert runner._ssh_user == "test_user"


def test_runner_run_dispatch(mocker, mock_app_version, mock_bfabric, tmp_path):
    """Test Runner.run_dispatch method"""
    mock_run = mocker.patch("subprocess.run")
    runner = Runner(spec=mock_app_version, client=mock_bfabric)
    workunit_ref = 123
    work_dir = tmp_path / "work"

    runner.run_dispatch(workunit_ref, work_dir)

    mock_run.assert_called_once_with(["mock-command", str(workunit_ref), str(work_dir)], check=True)


def test_runner_run_prepare_input(mocker, mock_app_version, mock_bfabric, tmp_path):
    """Test Runner.run_prepare_input method"""
    mock_prepare = mocker.patch("bfabric_app_runner.app_runner.runner.prepare_folder")
    runner = Runner(spec=mock_app_version, client=mock_bfabric, ssh_user="test_user")
    chunk_dir = tmp_path / "chunk"
    chunk_dir.mkdir()
    (chunk_dir / "inputs.yml").touch()

    runner.run_prepare_input(chunk_dir)

    mock_prepare.assert_called_once_with(
        inputs_yaml=chunk_dir / "inputs.yml",
        target_folder=chunk_dir,
        client=mock_bfabric,
        ssh_user="test_user",
        filter=None,
    )


def test_runner_run_process(mocker, mock_app_version, mock_bfabric, tmp_path):
    """Test Runner.run_process method"""
    mock_run = mocker.patch("subprocess.run")
    runner = Runner(spec=mock_app_version, client=mock_bfabric)
    chunk_dir = tmp_path / "chunk"

    runner.run_process(chunk_dir)

    mock_run.assert_called_once_with(["mock-command", str(chunk_dir)], check=True)


def test_run_app_full_workflow(mocker, mock_app_version, mock_bfabric, mock_workunit_definition, setup_work_dir):
    """Test complete run_app workflow"""
    # Setup mocks
    mocker.patch(
        "bfabric.experimental.workunit_definition.WorkunitDefinition.from_ref",
        return_value=mock_workunit_definition,
    )
    mock_run = mocker.patch("subprocess.run")
    mock_prepare = mocker.patch("bfabric_app_runner.app_runner.runner.prepare_folder")
    mock_register = mocker.patch("bfabric_app_runner.app_runner.runner.register_outputs")

    # Run the app
    run_app(
        app_spec=mock_app_version,
        workunit_ref=123,
        work_dir=setup_work_dir,
        client=mock_bfabric,
        ssh_user="test_user",
    )

    # Verify workflow steps
    assert mock_bfabric.save.call_count == 2  # Status updates at start and end
    assert mock_run.call_count == 3  # dispatch, process, collect
    assert mock_prepare.call_count == 1
    assert mock_register.call_count == 1


@pytest.mark.parametrize("read_only", [True, False])
def test_run_app_read_only_mode(
    mocker,
    read_only,
    mock_app_version,
    mock_bfabric,
    mock_workunit_definition,
    setup_work_dir,
):
    """Test run_app behavior in read-only mode"""
    mocker.patch(
        "bfabric.experimental.workunit_definition.WorkunitDefinition.from_ref",
        return_value=mock_workunit_definition,
    )
    mocker.patch("subprocess.run")
    mocker.patch("bfabric_app_runner.app_runner.runner.prepare_folder")
    mocker.patch("bfabric_app_runner.app_runner.runner.register_outputs")

    run_app(
        app_spec=mock_app_version,
        workunit_ref=123,
        work_dir=setup_work_dir,
        client=mock_bfabric,
        read_only=read_only,
    )

    # Verify status updates based on read_only mode
    expected_calls = 0 if read_only else 2
    assert mock_bfabric.save.call_count == expected_calls


def test_run_app_with_path_workunit_ref(
    mocker, mock_app_version, mock_bfabric, mock_workunit_definition, setup_work_dir
):
    """Test run_app with Path workunit_ref instead of int"""
    workunit_path = setup_work_dir / "workunit.yml"
    workunit_path.touch()

    mock_from_ref = mocker.patch(
        "bfabric.experimental.workunit_definition.WorkunitDefinition.from_ref",
        return_value=mock_workunit_definition,
    )
    mocker.patch("subprocess.run")
    mocker.patch("bfabric_app_runner.app_runner.runner.prepare_folder")
    mocker.patch("bfabric_app_runner.app_runner.runner.register_outputs")

    run_app(
        app_spec=mock_app_version,
        workunit_ref=workunit_path,
        work_dir=setup_work_dir,
        client=mock_bfabric,
    )

    # Verify workunit_ref was resolved
    mock_from_ref.assert_called_once()
    assert isinstance(mock_from_ref.call_args[1]["workunit"], Path)
    assert mock_from_ref.call_args[1]["workunit"].is_absolute()

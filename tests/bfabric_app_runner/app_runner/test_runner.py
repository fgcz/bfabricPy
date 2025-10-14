from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel

from bfabric_app_runner.app_runner.runner import Runner, run_app, ChunksFile


class MockCommand(BaseModel):
    name: str


class MockCommands(BaseModel):
    dispatch: MockCommand = MockCommand(name="dispatch")
    process: MockCommand = MockCommand(name="process")
    collect: MockCommand = MockCommand(name="collect")


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
def mock_execute_command(mocker):
    return mocker.patch("bfabric_app_runner.app_runner.runner.execute_command", autospec=True)


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


def test_runner_run_dispatch(mock_app_version, mock_bfabric, tmp_path, mock_execute_command):
    """Test Runner.run_dispatch method"""
    runner = Runner(spec=mock_app_version, client=mock_bfabric)
    workunit_ref = 123
    work_dir = tmp_path / "work"

    runner.run_dispatch(workunit_ref, work_dir)
    mock_execute_command.assert_called_once_with(MockCommand(name="dispatch"), str(workunit_ref), str(work_dir))


def test_runner_run_inputs(mocker, mock_app_version, mock_bfabric, tmp_path):
    """Test Runner.run_prepare_input method"""
    mock_prepare = mocker.patch("bfabric_app_runner.app_runner.runner.prepare_folder")
    runner = Runner(spec=mock_app_version, client=mock_bfabric, ssh_user="test_user")
    chunk_dir = tmp_path / "chunk"
    chunk_dir.mkdir()
    (chunk_dir / "inputs.yml").touch()

    runner.run_inputs(chunk_dir)

    mock_prepare.assert_called_once_with(
        inputs_yaml=chunk_dir / "inputs.yml",
        target_folder=chunk_dir,
        client=mock_bfabric,
        ssh_user="test_user",
        filter=None,
    )


def test_runner_run_process(mocker, mock_app_version, mock_bfabric, tmp_path, mock_execute_command):
    """Test Runner.run_process method"""
    runner = Runner(spec=mock_app_version, client=mock_bfabric)
    chunk_dir = tmp_path / "chunk"

    runner.run_process(chunk_dir)

    mock_execute_command.assert_called_once_with(MockCommand(name="process"), str(chunk_dir))


def test_run_app_full_workflow(
    mocker, mock_app_version, mock_bfabric, mock_workunit_definition, setup_work_dir, mock_execute_command
):
    """Test complete run_app workflow"""
    # Setup mocks
    mocker.patch(
        "bfabric.experimental.workunit_definition.WorkunitDefinition.from_ref",
        return_value=mock_workunit_definition,
    )
    mock_prepare = mocker.patch("bfabric_app_runner.app_runner.runner.prepare_folder")
    mock_register = mocker.patch("bfabric_app_runner.app_runner.runner.register_outputs")

    # Run the app
    run_app(
        app_spec=mock_app_version,
        workunit_ref=123,
        work_dir=setup_work_dir,
        client=mock_bfabric,
        ssh_user="test_user",
        force_storage=None,
    )

    # Verify workflow steps
    assert mock_bfabric.save.call_count == 2  # Status updates at start and end
    assert mock_execute_command.call_count == 3  # dispatch, process, collect
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
    mock_execute_command,
):
    """Test run_app behavior in read-only mode"""
    mocker.patch(
        "bfabric.experimental.workunit_definition.WorkunitDefinition.from_ref",
        return_value=mock_workunit_definition,
    )
    mocker.patch("bfabric_app_runner.app_runner.runner.prepare_folder")
    mocker.patch("bfabric_app_runner.app_runner.runner.register_outputs")

    run_app(
        app_spec=mock_app_version,
        workunit_ref=123,
        work_dir=setup_work_dir,
        client=mock_bfabric,
        read_only=read_only,
        force_storage=None,
    )

    # Verify status updates based on read_only mode
    expected_calls = 0 if read_only else 2
    assert mock_bfabric.save.call_count == expected_calls
    assert mock_execute_command.call_count == 3


def test_run_app_with_path_workunit_ref(
    mocker, mock_app_version, mock_bfabric, mock_workunit_definition, setup_work_dir, mock_execute_command
):
    """Test run_app with Path workunit_ref instead of int"""
    workunit_path = setup_work_dir / "workunit.yml"
    workunit_path.touch()

    mock_from_ref = mocker.patch(
        "bfabric.experimental.workunit_definition.WorkunitDefinition.from_ref",
        return_value=mock_workunit_definition,
    )
    mocker.patch("bfabric_app_runner.app_runner.runner.prepare_folder")
    mocker.patch("bfabric_app_runner.app_runner.runner.register_outputs")

    run_app(
        app_spec=mock_app_version,
        workunit_ref=workunit_path,
        work_dir=setup_work_dir,
        client=mock_bfabric,
        force_storage=None,
    )

    # Verify workunit_ref was resolved
    mock_from_ref.assert_called_once()
    assert isinstance(mock_from_ref.call_args[1]["workunit"], Path)
    assert mock_from_ref.call_args[1]["workunit"].is_absolute()
    assert mock_execute_command.call_count == 3


def test_chunks_file_infer_from_directory_basic(tmp_path):
    """Test basic chunk discovery from directory structure"""
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # Create chunk directories with inputs.yml
    (work_dir / "chunk1").mkdir()
    (work_dir / "chunk1" / "inputs.yml").touch()
    (work_dir / "chunk2").mkdir()
    (work_dir / "chunk2" / "inputs.yml").touch()

    chunks_file = ChunksFile.infer_from_directory(work_dir)

    assert len(chunks_file.chunks) == 2
    assert Path("chunk1") in chunks_file.chunks
    assert Path("chunk2") in chunks_file.chunks


def test_chunks_file_infer_from_directory_sorted(tmp_path):
    """Test that discovered chunks are sorted alphabetically"""
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # Create chunks in non-alphabetical order
    for chunk_name in ["zebra", "alpha", "beta"]:
        chunk_dir = work_dir / chunk_name
        chunk_dir.mkdir()
        (chunk_dir / "inputs.yml").touch()

    chunks_file = ChunksFile.infer_from_directory(work_dir)

    assert len(chunks_file.chunks) == 3
    assert chunks_file.chunks == [Path("alpha"), Path("beta"), Path("zebra")]


def test_chunks_file_infer_from_directory_empty(tmp_path):
    """Test that an error is raised when no chunks are found"""
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # Create some directories but without inputs.yml
    (work_dir / "empty_dir").mkdir()

    with pytest.raises(ValueError, match="No chunks found"):
        ChunksFile.infer_from_directory(work_dir)


def test_chunks_file_infer_ignores_nested(tmp_path):
    """Test that only 1 level deep directories are scanned"""
    from bfabric_app_runner.app_runner.runner import ChunksFile

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # Create a chunk at level 1
    (work_dir / "chunk1").mkdir()
    (work_dir / "chunk1" / "inputs.yml").touch()

    # Create a nested directory with inputs.yml (should be ignored)
    (work_dir / "chunk1" / "nested").mkdir()
    (work_dir / "chunk1" / "nested" / "inputs.yml").touch()

    chunks_file = ChunksFile.infer_from_directory(work_dir)

    assert len(chunks_file.chunks) == 1
    assert chunks_file.chunks == [Path("chunk1")]


def test_chunks_file_infer_ignores_files(tmp_path):
    """Test that files in work_dir are ignored, only directories considered"""
    from bfabric_app_runner.app_runner.runner import ChunksFile

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # Create a file named inputs.yml directly in work_dir (should be ignored)
    (work_dir / "inputs.yml").touch()

    # Create a proper chunk
    (work_dir / "chunk1").mkdir()
    (work_dir / "chunk1" / "inputs.yml").touch()

    chunks_file = ChunksFile.infer_from_directory(work_dir)

    assert len(chunks_file.chunks) == 1
    assert chunks_file.chunks == [Path("chunk1")]


def test_chunks_file_read_auto_discovers(tmp_path):
    """Test that read() falls back to auto-discovery when chunks.yml is missing"""
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # Create chunk directories with inputs.yml but no chunks.yml
    (work_dir / "chunk1").mkdir()
    (work_dir / "chunk1" / "inputs.yml").touch()
    (work_dir / "chunk2").mkdir()
    (work_dir / "chunk2" / "inputs.yml").touch()

    chunks_file = ChunksFile.read(work_dir)

    assert len(chunks_file.chunks) == 2
    assert Path("chunk1") in chunks_file.chunks
    assert Path("chunk2") in chunks_file.chunks


def test_chunks_file_read_writes_discovered(tmp_path):
    """Test that read() writes chunks.yml after auto-discovery"""
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # Create chunk directories with inputs.yml but no chunks.yml
    (work_dir / "chunk1").mkdir()
    (work_dir / "chunk1" / "inputs.yml").touch()

    # Verify chunks.yml doesn't exist
    assert not (work_dir / "chunks.yml").exists()

    # Call read which should auto-discover and write
    ChunksFile.read(work_dir)

    # Verify chunks.yml was created
    assert (work_dir / "chunks.yml").exists()

    # Verify contents
    chunks_content = yaml.safe_load((work_dir / "chunks.yml").read_text())
    assert chunks_content == {"chunks": ["chunk1"]}


def test_chunks_file_read_prefers_existing(tmp_path):
    """Test that read() uses existing chunks.yml if present"""
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # Create explicit chunks.yml with specific chunks
    explicit_chunks = {"chunks": ["explicit_chunk"]}
    (work_dir / "chunks.yml").write_text(yaml.dump(explicit_chunks))

    # Also create a different chunk directory that would be discovered
    (work_dir / "discovered_chunk").mkdir()
    (work_dir / "discovered_chunk" / "inputs.yml").touch()

    chunks_file = ChunksFile.read(work_dir)

    # Should use the explicit chunks.yml, not discover
    assert len(chunks_file.chunks) == 1
    assert chunks_file.chunks == [Path("explicit_chunk")]

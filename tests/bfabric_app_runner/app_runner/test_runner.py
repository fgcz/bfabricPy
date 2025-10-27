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
def mock_run_app_dependencies(mocker, mock_workunit_definition):
    """Fixture providing mocked dependencies for run_app tests"""

    class Mocks:
        workunit_def = mocker.patch(
            "bfabric.experimental.workunit_definition.WorkunitDefinition.from_ref",
            return_value=mock_workunit_definition,
        )
        prepare_folder = mocker.patch("bfabric_app_runner.app_runner.runner.prepare_folder")
        register_outputs = mocker.patch("bfabric_app_runner.app_runner.runner.register_outputs")

    return Mocks()


@pytest.fixture
def work_dir(tmp_path):
    """Fixture providing a clean work directory"""
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    return work_dir


@pytest.fixture
def work_dir_with_chunks(work_dir):
    """Fixture providing a work directory with chunks.yml and a chunk"""
    chunk_dir = create_chunk(work_dir, "chunk1")
    (chunk_dir / "outputs.yml").touch()

    chunks_yaml = {"chunks": [str(chunk_dir)]}
    (work_dir / "chunks.yml").write_text(yaml.dump(chunks_yaml))

    return work_dir


def create_chunk(work_dir: Path, chunk_name: str) -> Path:
    """Helper function to create a chunk directory with inputs.yml"""
    chunk_dir = work_dir / chunk_name
    chunk_dir.mkdir()
    (chunk_dir / "inputs.yml").touch()
    return chunk_dir


class TestRunner:
    """Tests for the Runner class"""

    def test_initialization(self, mock_app_version, mock_bfabric):
        """Test Runner initialization"""
        runner = Runner(spec=mock_app_version, client=mock_bfabric, ssh_user="test_user")
        assert runner._app_version == mock_app_version
        assert runner._client == mock_bfabric
        assert runner._ssh_user == "test_user"

    def test_run_dispatch(self, mock_app_version, mock_bfabric, work_dir, mock_execute_command):
        """Test Runner.run_dispatch method"""
        runner = Runner(spec=mock_app_version, client=mock_bfabric)
        workunit_ref = 123

        runner.run_dispatch(workunit_ref, work_dir)

        mock_execute_command.assert_called_once_with(MockCommand(name="dispatch"), str(workunit_ref), str(work_dir))

    def test_run_inputs(self, mocker, mock_app_version, mock_bfabric, work_dir):
        """Test Runner.run_inputs method"""
        mock_prepare = mocker.patch("bfabric_app_runner.app_runner.runner.prepare_folder")
        runner = Runner(spec=mock_app_version, client=mock_bfabric, ssh_user="test_user")
        chunk_dir = create_chunk(work_dir, "chunk")

        runner.run_inputs(chunk_dir)

        mock_prepare.assert_called_once_with(
            inputs_yaml=chunk_dir / "inputs.yml",
            target_folder=chunk_dir,
            client=mock_bfabric,
            ssh_user="test_user",
            filter=None,
        )

    def test_run_process(self, mock_app_version, mock_bfabric, work_dir, mock_execute_command):
        """Test Runner.run_process method"""
        runner = Runner(spec=mock_app_version, client=mock_bfabric)
        chunk_dir = work_dir / "chunk"

        runner.run_process(chunk_dir)

        mock_execute_command.assert_called_once_with(MockCommand(name="process"), str(chunk_dir))


class TestRunApp:
    """Tests for the run_app function"""

    def test_full_workflow(
        self, mock_app_version, mock_bfabric, work_dir_with_chunks, mock_execute_command, mock_run_app_dependencies
    ):
        """Test complete run_app workflow"""
        run_app(
            app_spec=mock_app_version,
            workunit_ref=123,
            work_dir=work_dir_with_chunks,
            client=mock_bfabric,
            ssh_user="test_user",
            force_storage=None,
        )

        assert mock_bfabric.save.call_count == 2  # Status updates at start and end
        assert mock_execute_command.call_count == 3  # dispatch, process, collect
        assert mock_run_app_dependencies.prepare_folder.call_count == 1
        assert mock_run_app_dependencies.register_outputs.call_count == 1

    @pytest.mark.parametrize("read_only", [True, False])
    def test_read_only_mode(
        self,
        read_only,
        mock_app_version,
        mock_bfabric,
        work_dir_with_chunks,
        mock_execute_command,
        mock_run_app_dependencies,
    ):
        """Test run_app behavior in read-only mode"""
        run_app(
            app_spec=mock_app_version,
            workunit_ref=123,
            work_dir=work_dir_with_chunks,
            client=mock_bfabric,
            read_only=read_only,
            force_storage=None,
        )

        expected_calls = 0 if read_only else 2
        assert mock_bfabric.save.call_count == expected_calls
        assert mock_execute_command.call_count == 3

    def test_with_path_workunit_ref(
        self, mock_app_version, mock_bfabric, work_dir_with_chunks, mock_execute_command, mock_run_app_dependencies
    ):
        """Test run_app with Path workunit_ref instead of int"""
        workunit_path = work_dir_with_chunks / "workunit.yml"
        workunit_path.touch()

        run_app(
            app_spec=mock_app_version,
            workunit_ref=workunit_path,
            work_dir=work_dir_with_chunks,
            client=mock_bfabric,
            force_storage=None,
        )

        mock_run_app_dependencies.workunit_def.assert_called_once()
        assert isinstance(mock_run_app_dependencies.workunit_def.call_args[1]["workunit"], Path)
        assert mock_run_app_dependencies.workunit_def.call_args[1]["workunit"].is_absolute()
        assert mock_execute_command.call_count == 3


class TestChunksFileInfer:
    """Tests for ChunksFile.infer_from_directory() method"""

    def test_basic_discovery(self, work_dir):
        """Test basic chunk discovery from directory structure"""
        create_chunk(work_dir, "chunk1")
        create_chunk(work_dir, "chunk2")

        chunks_file = ChunksFile.infer_from_directory(work_dir)

        assert len(chunks_file.chunks) == 2
        assert Path("chunk1") in chunks_file.chunks
        assert Path("chunk2") in chunks_file.chunks

    def test_sorted_alphabetically(self, work_dir):
        """Test that discovered chunks are sorted alphabetically"""
        for chunk_name in ["zebra", "alpha", "beta"]:
            create_chunk(work_dir, chunk_name)

        chunks_file = ChunksFile.infer_from_directory(work_dir)

        assert chunks_file.chunks == [Path("alpha"), Path("beta"), Path("zebra")]

    def test_no_chunks_found(self, work_dir):
        """Test that an error is raised when no chunks are found"""
        (work_dir / "empty_dir").mkdir()

        with pytest.raises(ValueError, match="No chunks found"):
            ChunksFile.infer_from_directory(work_dir)

    def test_ignores_nested_directories(self, work_dir):
        """Test that only 1 level deep directories are scanned"""
        create_chunk(work_dir, "chunk1")
        # Create a nested directory with inputs.yml (should be ignored)
        (work_dir / "chunk1" / "nested").mkdir()
        (work_dir / "chunk1" / "nested" / "inputs.yml").touch()

        chunks_file = ChunksFile.infer_from_directory(work_dir)

        assert len(chunks_file.chunks) == 1
        assert chunks_file.chunks == [Path("chunk1")]

    def test_ignores_files(self, work_dir):
        """Test that files in work_dir are ignored"""
        (work_dir / "inputs.yml").touch()
        create_chunk(work_dir, "chunk1")

        chunks_file = ChunksFile.infer_from_directory(work_dir)

        assert len(chunks_file.chunks) == 1
        assert chunks_file.chunks == [Path("chunk1")]


class TestChunksFileRead:
    """Tests for ChunksFile.read() method with auto-discovery"""

    def test_auto_discovers_when_missing(self, work_dir):
        """Test that read() falls back to auto-discovery when chunks.yml is missing"""
        create_chunk(work_dir, "chunk1")
        create_chunk(work_dir, "chunk2")

        chunks_file = ChunksFile.read(work_dir)

        assert len(chunks_file.chunks) == 2
        assert Path("chunk1") in chunks_file.chunks
        assert Path("chunk2") in chunks_file.chunks

    def test_writes_discovered_chunks(self, work_dir):
        """Test that read() writes chunks.yml after auto-discovery"""
        create_chunk(work_dir, "chunk1")

        assert not (work_dir / "chunks.yml").exists()

        ChunksFile.read(work_dir)

        assert (work_dir / "chunks.yml").exists()
        chunks_content = yaml.safe_load((work_dir / "chunks.yml").read_text())
        assert chunks_content == {"chunks": ["chunk1"]}

    def test_prefers_existing_file(self, work_dir):
        """Test that read() uses existing chunks.yml if present"""
        explicit_chunks = {"chunks": ["explicit_chunk"]}
        (work_dir / "chunks.yml").write_text(yaml.dump(explicit_chunks))
        create_chunk(work_dir, "discovered_chunk")

        chunks_file = ChunksFile.read(work_dir)

        assert len(chunks_file.chunks) == 1
        assert chunks_file.chunks == [Path("explicit_chunk")]

from pathlib import Path
import zipfile
import tempfile

import pytest
from bfabric_app_runner.inputs.prepare.prepare_resolved_directory import (
    prepare_resolved_directory,
    _download_file,
    _extract_zip_with_filtering,
    _filter_files,
    _get_output_file_path,
)
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedDirectory
from bfabric_app_runner.specs.inputs.file_spec import FileSourceLocal, FileSourceSsh, FileSourceSshValue


@pytest.fixture
def mock_prepare_resolved_file(mocker):
    return mocker.patch("bfabric_app_runner.inputs.prepare.prepare_resolved_directory.prepare_resolved_file")


@pytest.fixture
def temp_zip_file():
    """Create a temporary zip file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
        temp_path = Path(temp_file.name)

    # Create a zip file with some test content
    with zipfile.ZipFile(temp_path, "w") as zip_file:
        zip_file.writestr("root/file1.txt", "content1")
        zip_file.writestr("root/subdir/file2.txt", "content2")
        zip_file.writestr("root/file3.log", "log content")
        zip_file.writestr("other/file4.txt", "content4")

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


def test_prepare_resolved_directory_zip_extraction(temp_zip_file, tmp_path):
    """Test basic zip extraction functionality."""
    directory = ResolvedDirectory(
        source=FileSourceLocal(local=str(temp_zip_file)),
        filename="extracted",
        extract="zip",
        include_patterns=[],
        exclude_patterns=[],
        strip_root=False,
    )

    prepare_resolved_directory(directory, tmp_path, ssh_user=None)

    # Check extracted files
    extracted_path = tmp_path / "extracted"
    assert extracted_path.exists()
    assert (extracted_path / "root" / "file1.txt").exists()
    assert (extracted_path / "root" / "subdir" / "file2.txt").exists()
    assert (extracted_path / "root" / "file3.log").exists()
    assert (extracted_path / "other" / "file4.txt").exists()

    # Check file contents
    assert (extracted_path / "root" / "file1.txt").read_text() == "content1"
    assert (extracted_path / "root" / "subdir" / "file2.txt").read_text() == "content2"


def test_prepare_resolved_directory_with_strip_root(temp_zip_file, tmp_path):
    """Test zip extraction with root directory stripping."""
    directory = ResolvedDirectory(
        source=FileSourceLocal(local=str(temp_zip_file)),
        filename="extracted",
        extract="zip",
        include_patterns=[],
        exclude_patterns=[],
        strip_root=True,
    )

    prepare_resolved_directory(directory, tmp_path, ssh_user=None)

    # Check that root directory was stripped
    extracted_path = tmp_path / "extracted"
    assert extracted_path.exists()
    assert (extracted_path / "file1.txt").exists()  # root/ stripped
    assert (extracted_path / "subdir" / "file2.txt").exists()  # root/ stripped
    assert (extracted_path / "file3.log").exists()  # root/ stripped
    assert (extracted_path / "file4.txt").exists()  # other/ also stripped (first level)


def test_prepare_resolved_directory_with_include_patterns(temp_zip_file, tmp_path):
    """Test zip extraction with include patterns."""
    directory = ResolvedDirectory(
        source=FileSourceLocal(local=str(temp_zip_file)),
        filename="extracted",
        extract="zip",
        include_patterns=["*.txt"],
        exclude_patterns=[],
        strip_root=False,
    )

    prepare_resolved_directory(directory, tmp_path, ssh_user=None)

    # Check that only .txt files were extracted
    extracted_path = tmp_path / "extracted"
    assert extracted_path.exists()
    assert (extracted_path / "root" / "file1.txt").exists()
    assert (extracted_path / "root" / "subdir" / "file2.txt").exists()
    assert not (extracted_path / "root" / "file3.log").exists()  # .log excluded
    assert (extracted_path / "other" / "file4.txt").exists()


def test_prepare_resolved_directory_with_exclude_patterns(temp_zip_file, tmp_path):
    """Test zip extraction with exclude patterns."""
    directory = ResolvedDirectory(
        source=FileSourceLocal(local=str(temp_zip_file)),
        filename="extracted",
        extract="zip",
        include_patterns=[],
        exclude_patterns=["*.log"],
        strip_root=False,
    )

    prepare_resolved_directory(directory, tmp_path, ssh_user=None)

    # Check that .log files were excluded
    extracted_path = tmp_path / "extracted"
    assert extracted_path.exists()
    assert (extracted_path / "root" / "file1.txt").exists()
    assert (extracted_path / "root" / "subdir" / "file2.txt").exists()
    assert not (extracted_path / "root" / "file3.log").exists()  # .log excluded
    assert (extracted_path / "other" / "file4.txt").exists()


def test_prepare_resolved_directory_unsupported_extract():
    """Test that unsupported extraction types raise an error."""
    # Create a directory with None extract to test the error path
    directory = ResolvedDirectory(
        source=FileSourceLocal(local="/test.tar.gz"),
        filename="extracted",
        extract=None,  # Not supported
        include_patterns=[],
        exclude_patterns=[],
        strip_root=False,
    )

    with pytest.raises(NotImplementedError, match="Extraction type None not supported"):
        prepare_resolved_directory(directory, Path("/tmp"), ssh_user=None)


def test_download_file_success(mock_prepare_resolved_file, tmp_path):
    """Test downloading with success."""
    directory = ResolvedDirectory(
        source=FileSourceLocal(local="/source.zip"),
        filename="test",
        extract="zip",
        include_patterns=[],
        exclude_patterns=[],
        strip_root=False,
    )

    result = _download_file(directory, tmp_path / "test.zip", ssh_user=None)

    mock_prepare_resolved_file.assert_called_once()
    # Verify the ResolvedFile was created correctly
    call_args = mock_prepare_resolved_file.call_args
    resolved_file = call_args[0][0]  # First positional argument
    assert resolved_file.source == directory.source
    assert resolved_file.filename == "test.zip"
    assert resolved_file.link is False
    assert resolved_file.checksum is None
    assert result


def test_download_file_failure(mock_prepare_resolved_file, tmp_path):
    """Test downloading with failure."""
    mock_prepare_resolved_file.side_effect = RuntimeError("Download failed")
    directory = ResolvedDirectory(
        source=FileSourceLocal(local="/source.zip"),
        filename="test",
        extract="zip",
        include_patterns=[],
        exclude_patterns=[],
        strip_root=False,
    )

    result = _download_file(directory, tmp_path / "test.zip", ssh_user=None)

    mock_prepare_resolved_file.assert_called_once()
    assert not result


def test_download_file_ssh_source(mock_prepare_resolved_file, tmp_path):
    """Test downloading from SSH source."""
    directory = ResolvedDirectory(
        source=FileSourceSsh(ssh=FileSourceSshValue(host="host", path="/source.zip")),
        filename="test",
        extract="zip",
        include_patterns=[],
        exclude_patterns=[],
        strip_root=False,
    )

    result = _download_file(directory, tmp_path / "test.zip", ssh_user="user")

    mock_prepare_resolved_file.assert_called_once()
    # Verify the ResolvedFile was created correctly
    call_args = mock_prepare_resolved_file.call_args
    resolved_file = call_args[0][0]  # First positional argument
    assert resolved_file.source == directory.source
    assert call_args[0][2] == "user"  # Third positional argument (ssh_user)
    assert result


def test_filter_files_no_patterns():
    """Test file filtering with no patterns."""
    files = ["file1.txt", "file2.py", "file3.log"]
    result = _filter_files(files, [], [])
    assert result == files


def test_filter_files_include_patterns():
    """Test file filtering with include patterns."""
    files = ["file1.txt", "file2.py", "file3.log", "file4.txt"]
    result = _filter_files(files, ["*.txt"], [])
    assert result == ["file1.txt", "file4.txt"]


def test_filter_files_exclude_patterns():
    """Test file filtering with exclude patterns."""
    files = ["file1.txt", "file2.py", "file3.log", "file4.txt"]
    result = _filter_files(files, [], ["*.log"])
    assert result == ["file1.txt", "file2.py", "file4.txt"]


def test_filter_files_include_and_exclude():
    """Test file filtering with both include and exclude patterns."""
    files = ["file1.txt", "file2.py", "file3.log", "test.txt"]
    result = _filter_files(files, ["*.txt"], ["test*"])
    assert result == ["file1.txt"]


def test_get_output_file_path_no_strip():
    """Test output file path without stripping root."""
    result = _get_output_file_path("root/subdir/file.txt", Path("/output"), False)
    assert result == Path("/output/root/subdir/file.txt")


def test_get_output_file_path_with_strip():
    """Test output file path with stripping root."""
    result = _get_output_file_path("root/subdir/file.txt", Path("/output"), True)
    assert result == Path("/output/subdir/file.txt")


def test_get_output_file_path_strip_single_level():
    """Test output file path with stripping when only one level."""
    result = _get_output_file_path("file.txt", Path("/output"), True)
    assert result == Path("/output/file.txt")

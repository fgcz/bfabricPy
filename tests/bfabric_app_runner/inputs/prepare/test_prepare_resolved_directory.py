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
    _should_strip_root_directory,
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

    # Check that zip file is left in working directory for caching
    zip_file_path = tmp_path / "extracted.zip"
    assert zip_file_path.exists()

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


def test_prepare_resolved_directory_with_strip_root_multiple_dirs(temp_zip_file, tmp_path):
    """Test zip extraction with root directory stripping when there are multiple root dirs."""
    directory = ResolvedDirectory(
        source=FileSourceLocal(local=str(temp_zip_file)),
        filename="extracted",
        extract="zip",
        include_patterns=[],
        exclude_patterns=[],
        strip_root=True,
    )

    prepare_resolved_directory(directory, tmp_path, ssh_user=None)

    # Check that zip file is left in working directory for caching
    zip_file_path = tmp_path / "extracted.zip"
    assert zip_file_path.exists()

    # Check that root directory was NOT stripped (because there are multiple root dirs)
    extracted_path = tmp_path / "extracted"
    assert extracted_path.exists()
    assert (extracted_path / "root" / "file1.txt").exists()  # root/ NOT stripped
    assert (extracted_path / "root" / "subdir" / "file2.txt").exists()  # root/ NOT stripped
    assert (extracted_path / "root" / "file3.log").exists()  # root/ NOT stripped
    assert (extracted_path / "other" / "file4.txt").exists()  # other/ NOT stripped


def test_prepare_resolved_directory_with_strip_root_single_dir(tmp_path):
    """Test zip extraction with root directory stripping when there's a single root dir."""
    # Create a zip file with only one root directory
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        # Create a zip file with single root directory
        with zipfile.ZipFile(temp_path, "w") as zip_file:
            zip_file.writestr("project/src/file1.py", "content1")
            zip_file.writestr("project/README.md", "content2")
            zip_file.writestr("project/subdir/file2.py", "content3")

        directory = ResolvedDirectory(
            source=FileSourceLocal(local=str(temp_path)),
            filename="extracted",
            extract="zip",
            include_patterns=[],
            exclude_patterns=[],
            strip_root=True,
        )

        prepare_resolved_directory(directory, tmp_path, ssh_user=None)

        # Check that zip file is left in working directory for caching
        zip_file_path = tmp_path / "extracted.zip"
        assert zip_file_path.exists()

        # Check that root directory WAS stripped (single root directory)
        extracted_path = tmp_path / "extracted"
        assert extracted_path.exists()
        assert (extracted_path / "src" / "file1.py").exists()  # project/ stripped
        assert (extracted_path / "README.md").exists()  # project/ stripped
        assert (extracted_path / "subdir" / "file2.py").exists()  # project/ stripped

        # Check file contents
        assert (extracted_path / "src" / "file1.py").read_text() == "content1"
        assert (extracted_path / "README.md").read_text() == "content2"

    finally:
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()


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

    # Check that zip file is left in working directory for caching
    zip_file_path = tmp_path / "extracted.zip"
    assert zip_file_path.exists()

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

    # Check that zip file is left in working directory for caching
    zip_file_path = tmp_path / "extracted.zip"
    assert zip_file_path.exists()

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

    # Should not raise an exception
    _download_file(directory, tmp_path / "test.zip", ssh_user=None)

    mock_prepare_resolved_file.assert_called_once()
    # Verify the ResolvedFile was created correctly
    call_args = mock_prepare_resolved_file.call_args
    resolved_file = call_args[1]["file"]  # file keyword argument
    assert resolved_file.source == directory.source
    assert resolved_file.filename == "test.zip"
    assert resolved_file.link is False
    assert resolved_file.checksum is None


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

    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="Download failed"):
        _download_file(directory, tmp_path / "test.zip", ssh_user=None)

    mock_prepare_resolved_file.assert_called_once()


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

    # Should not raise an exception
    _download_file(directory, tmp_path / "test.zip", ssh_user="user")

    mock_prepare_resolved_file.assert_called_once()
    # Verify the ResolvedFile was created correctly
    call_args = mock_prepare_resolved_file.call_args
    resolved_file = call_args[1]["file"]  # file keyword argument
    assert resolved_file.source == directory.source
    # ssh_user is passed as keyword argument to prepare_resolved_file
    assert call_args[1]["ssh_user"] == "user"


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


def test_should_strip_root_directory_single_root_dir():
    """Test should strip when there's a single root directory."""
    files = ["project/src/file.py", "project/README.md", "project/"]
    assert _should_strip_root_directory(files) is True


def test_should_strip_root_directory_multiple_root_entries():
    """Test should not strip when there are multiple root entries."""
    files = ["project/file.py", "README.md", "other/file.txt"]
    assert _should_strip_root_directory(files) is False


def test_should_strip_root_directory_single_root_file():
    """Test should not strip when there's only a single root file."""
    files = ["single_file.txt"]
    assert _should_strip_root_directory(files) is False


def test_should_strip_root_directory_multiple_root_files():
    """Test should not strip when there are multiple root files."""
    files = ["file1.txt", "file2.txt", "file3.txt"]
    assert _should_strip_root_directory(files) is False


def test_should_strip_root_directory_empty_list():
    """Test should not strip when file list is empty."""
    files = []
    assert _should_strip_root_directory(files) is False


def test_should_strip_root_directory_mixed_scenario():
    """Test should not strip when there's a mix of root dir and files."""
    files = ["project/src/file.py", "standalone.txt"]
    assert _should_strip_root_directory(files) is False


def test_caching_behavior_zip_file_reuse(temp_zip_file, tmp_path):
    """Test that zip file is left in working directory for caching."""
    directory = ResolvedDirectory(
        source=FileSourceLocal(local=str(temp_zip_file)),
        filename="cached_extract",
        extract="zip",
        include_patterns=[],
        exclude_patterns=[],
        strip_root=False,
    )

    # First extraction
    prepare_resolved_directory(directory, tmp_path, ssh_user=None)

    # Verify zip file exists and extraction worked
    zip_file_path = tmp_path / "cached_extract.zip"
    extracted_path = tmp_path / "cached_extract"
    assert zip_file_path.exists()
    assert extracted_path.exists()
    assert (extracted_path / "root" / "file1.txt").exists()

    # Get the modification time of the zip file
    first_mtime = zip_file_path.stat().st_mtime

    # Second extraction (should reuse zip file via rsync caching)
    # For local files, rsync would detect the file is unchanged and skip download
    prepare_resolved_directory(directory, tmp_path, ssh_user=None)

    # Verify zip file still exists and extraction still works
    assert zip_file_path.exists()
    assert extracted_path.exists()
    assert (extracted_path / "root" / "file1.txt").exists()

    # The zip file should still be there for caching
    # (In real usage, rsync would handle the caching optimization)
    assert zip_file_path.stat().st_mtime >= first_mtime

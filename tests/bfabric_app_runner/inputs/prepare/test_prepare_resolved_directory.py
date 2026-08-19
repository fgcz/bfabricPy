import os
import tempfile
import zipfile
from pathlib import Path

import pytest
from bfabric.transfer import md5_checksum

from bfabric_app_runner.inputs.prepare.prepare_context import PrepareContext
from bfabric_app_runner.inputs.prepare.prepare_resolved_directory import (
    prepare_resolved_directory,
    _crc32,
    _download_file,
    _get_output_file_path,
    _is_entry_current,
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

    prepare_resolved_directory(directory, tmp_path, PrepareContext())

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

    prepare_resolved_directory(directory, tmp_path, PrepareContext())

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

        prepare_resolved_directory(directory, tmp_path, PrepareContext())

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

    prepare_resolved_directory(directory, tmp_path, PrepareContext())

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

    prepare_resolved_directory(directory, tmp_path, PrepareContext())

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
        prepare_resolved_directory(directory, Path("/tmp"), PrepareContext())


def test_download_file_success(mock_prepare_resolved_file, tmp_path):
    """Test downloading with success."""
    directory = ResolvedDirectory(
        source=FileSourceLocal(local="/source.zip"),
        filename="test",
        extract="zip",
        include_patterns=[],
        exclude_patterns=[],
        strip_root=False,
        checksum="d41d8cd98f00b204e9800998ecf8427e",
    )

    # Should not raise an exception
    _download_file(directory, tmp_path / "test.zip", PrepareContext())

    mock_prepare_resolved_file.assert_called_once()
    # Verify the ResolvedFile was created correctly
    call_args = mock_prepare_resolved_file.call_args
    resolved_file = call_args[1]["file"]  # file keyword argument
    assert resolved_file.source == directory.source
    assert resolved_file.filename == "test.zip"
    assert resolved_file.link is False
    # The archive is verified against the resource checksum after the transfer.
    assert resolved_file.checksum == "d41d8cd98f00b204e9800998ecf8427e"


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
        _download_file(directory, tmp_path / "test.zip", PrepareContext())

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
    _download_file(directory, tmp_path / "test.zip", PrepareContext(ssh_user="user"))

    mock_prepare_resolved_file.assert_called_once()
    # Verify the ResolvedFile was created correctly
    call_args = mock_prepare_resolved_file.call_args
    resolved_file = call_args[1]["file"]  # file keyword argument
    assert resolved_file.source == directory.source
    # the prepare context (carrying ssh_user) is forwarded to prepare_resolved_file
    assert call_args[1]["context"] == PrepareContext(ssh_user="user")


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


def test_prepare_resolved_directory_subdirectory_filename(temp_zip_file, tmp_path):
    """Regression test for issue #323: zip written to wrong path when filename has a subdirectory."""
    directory = ResolvedDirectory(
        source=FileSourceLocal(local=str(temp_zip_file)),
        filename="input/result",
        extract="zip",
        include_patterns=[],
        exclude_patterns=[],
        strip_root=False,
    )

    prepare_resolved_directory(directory, tmp_path, PrepareContext())

    # Zip must land at tmp_path/input/result.zip, NOT tmp_path/input/input/result.zip
    assert (tmp_path / "input" / "result.zip").exists()
    assert not (tmp_path / "input" / "input").exists()

    # Extraction target
    extracted_path = tmp_path / "input" / "result"
    assert extracted_path.exists()
    assert (extracted_path / "root" / "file1.txt").exists()


class TestSkipUnchangedEntries:
    """A repeated prepare must not redo work, but must repair any extracted file that no longer matches."""

    # An mtime far enough in the past that a re-extraction is unmistakable.
    OLD_MTIME = 1000000000

    @pytest.fixture
    def directory(self, temp_zip_file):
        return ResolvedDirectory(
            source=FileSourceLocal(local=str(temp_zip_file)),
            filename="extracted",
            extract="zip",
            include_patterns=[],
            exclude_patterns=[],
            strip_root=False,
        )

    @staticmethod
    def _backdate(path: Path) -> None:
        os.utime(path, (TestSkipUnchangedEntries.OLD_MTIME, TestSkipUnchangedEntries.OLD_MTIME))

    def _prepare_twice(self, directory, tmp_path, modify=None):
        """Prepares, backdates every extracted file, optionally mutates the tree, then prepares again."""
        prepare_resolved_directory(directory, tmp_path, PrepareContext())
        extracted_path = tmp_path / "extracted"
        for path in sorted(p for p in extracted_path.rglob("*") if p.is_file()):
            self._backdate(path)
        if modify is not None:
            modify(extracted_path)
        prepare_resolved_directory(directory, tmp_path, PrepareContext())
        return extracted_path

    def test_unchanged_files_are_not_re_extracted(self, directory, tmp_path):
        extracted_path = self._prepare_twice(directory, tmp_path)

        for path in (p for p in extracted_path.rglob("*") if p.is_file()):
            assert path.stat().st_mtime == self.OLD_MTIME, f"{path} was re-extracted"

    def test_modified_file_of_same_size_is_restored(self, directory, tmp_path):
        # Same byte count as "content1", so only the CRC32 can tell the two apart.
        def modify(extracted_path: Path) -> None:
            (extracted_path / "root" / "file1.txt").write_text("CONTENT1")

        extracted_path = self._prepare_twice(directory, tmp_path, modify)

        modified = extracted_path / "root" / "file1.txt"
        assert modified.read_text() == "content1"
        assert modified.stat().st_mtime != self.OLD_MTIME
        # The untouched siblings are still left alone.
        assert (extracted_path / "root" / "subdir" / "file2.txt").stat().st_mtime == self.OLD_MTIME

    def test_truncated_file_is_restored(self, directory, tmp_path):
        def modify(extracted_path: Path) -> None:
            (extracted_path / "root" / "file1.txt").write_text("c")

        extracted_path = self._prepare_twice(directory, tmp_path, modify)

        assert (extracted_path / "root" / "file1.txt").read_text() == "content1"

    def test_deleted_file_is_restored(self, directory, tmp_path):
        def modify(extracted_path: Path) -> None:
            (extracted_path / "root" / "file1.txt").unlink()

        extracted_path = self._prepare_twice(directory, tmp_path, modify)

        assert (extracted_path / "root" / "file1.txt").read_text() == "content1"


class TestSkipDownload:
    """The archive is re-downloaded unless the cached copy provably matches the resource checksum."""

    @pytest.fixture
    def cached_zip(self, temp_zip_file, tmp_path):
        """Puts the archive where prepare caches it, and returns its checksum."""
        cache_path = tmp_path / "extracted.zip"
        _ = cache_path.write_bytes(temp_zip_file.read_bytes())
        return md5_checksum(cache_path)

    @staticmethod
    def _directory(temp_zip_file, checksum):
        return ResolvedDirectory(
            source=FileSourceLocal(local=str(temp_zip_file)),
            filename="extracted",
            extract="zip",
            include_patterns=[],
            exclude_patterns=[],
            strip_root=False,
            checksum=checksum,
        )

    def test_skips_download_when_cached_zip_matches(
        self, mock_prepare_resolved_file, temp_zip_file, cached_zip, tmp_path
    ):
        directory = self._directory(temp_zip_file, cached_zip)

        prepare_resolved_directory(directory, tmp_path, PrepareContext())

        mock_prepare_resolved_file.assert_not_called()
        # The cached archive is still extracted, i.e. skipping the transfer does not skip the work.
        assert (tmp_path / "extracted" / "root" / "file1.txt").read_text() == "content1"

    def test_downloads_when_cached_zip_does_not_match(
        self, mock_prepare_resolved_file, temp_zip_file, cached_zip, tmp_path
    ):
        directory = self._directory(temp_zip_file, "0" * 32)

        prepare_resolved_directory(directory, tmp_path, PrepareContext())

        mock_prepare_resolved_file.assert_called_once()

    def test_downloads_when_no_checksum_available(
        self, mock_prepare_resolved_file, temp_zip_file, cached_zip, tmp_path
    ):
        directory = self._directory(temp_zip_file, None)

        prepare_resolved_directory(directory, tmp_path, PrepareContext())

        mock_prepare_resolved_file.assert_called_once()


class TestIsEntryCurrent:
    @pytest.fixture
    def zip_info(self, temp_zip_file):
        with zipfile.ZipFile(temp_zip_file) as zip_ref:
            return zip_ref.getinfo("root/file1.txt")

    def test_matching_file(self, zip_info, tmp_path):
        path = tmp_path / "file1.txt"
        _ = path.write_text("content1")
        assert _is_entry_current(zip_info, path) is True

    def test_missing_file(self, zip_info, tmp_path):
        assert _is_entry_current(zip_info, tmp_path / "absent.txt") is False

    def test_same_size_different_content(self, zip_info, tmp_path):
        path = tmp_path / "file1.txt"
        _ = path.write_text("CONTENT1")
        assert _is_entry_current(zip_info, path) is False

    def test_different_size(self, zip_info, tmp_path):
        path = tmp_path / "file1.txt"
        _ = path.write_text("content1-and-more")
        assert _is_entry_current(zip_info, path) is False

    def test_directory_in_place_of_file(self, zip_info, tmp_path):
        path = tmp_path / "file1.txt"
        path.mkdir()
        assert _is_entry_current(zip_info, path) is False

    def test_crc32_matches_zip_entry_crc(self, zip_info, tmp_path):
        path = tmp_path / "file1.txt"
        _ = path.write_text("content1")
        assert _crc32(path) == zip_info.CRC

    def test_crc32_is_chunk_size_independent(self, tmp_path):
        path = tmp_path / "large.bin"
        _ = path.write_bytes(b"0123456789" * 1000)
        assert _crc32(path, chunk_size=7) == _crc32(path)

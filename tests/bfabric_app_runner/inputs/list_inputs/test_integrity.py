import zipfile
from pathlib import Path

import pytest
from bfabric.transfer import md5_checksum

from bfabric_app_runner.inputs.list_inputs.integrity import IntegrityState, check_integrity
from bfabric_app_runner.inputs.prepare.prepare_context import PrepareContext
from bfabric_app_runner.inputs.prepare.prepare_resolved_directory import prepare_resolved_directory
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedDirectory
from bfabric_app_runner.specs.inputs.file_spec import FileSourceLocal


@pytest.fixture
def mock_client(mocker):
    """The client is only needed by the signature; the directory checks never use it."""
    return mocker.Mock(name="client")


@pytest.fixture
def source_zip(tmp_path):
    path = tmp_path / "source" / "archive.zip"
    path.parent.mkdir()
    with zipfile.ZipFile(path, "w") as zip_file:
        zip_file.writestr("root/file1.txt", "content1")
        zip_file.writestr("root/subdir/file2.txt", "content2")
    return path


class TestDirectoryIntegrity:
    """``inputs check`` must report Incorrect exactly when a prepare would have work to do."""

    @pytest.fixture
    def target(self, tmp_path):
        return tmp_path / "target"

    def _prepared(self, source_zip, target, filename="extracted", **kwargs):
        """Prepares the archive under ``target`` and returns the matching resolved input."""
        directory = ResolvedDirectory(
            source=FileSourceLocal(local=str(source_zip)),
            filename=filename,
            extract="zip",
            checksum=md5_checksum(source_zip),
            **kwargs,
        )
        prepare_resolved_directory(directory, target, PrepareContext())
        return directory

    def test_correct_after_prepare(self, source_zip, target, mock_client):
        directory = self._prepared(source_zip, target)

        state = check_integrity(file=directory, local_path=target / "extracted", client=mock_client)

        assert state == IntegrityState.Correct

    def test_correct_for_nested_filename(self, source_zip, target, mock_client):
        """Regression test for the issue #323 cache path: the archive sits inside the subdirectory."""
        directory = self._prepared(source_zip, target, filename="input/extracted")

        state = check_integrity(file=directory, local_path=target / "input" / "extracted", client=mock_client)

        assert state == IntegrityState.Correct

    def test_incorrect_when_extracted_file_modified(self, source_zip, target, mock_client):
        directory = self._prepared(source_zip, target)
        # Same size as the original, so only the CRC32 can tell them apart.
        _ = (target / "extracted" / "root" / "file1.txt").write_text("CONTENT1")

        state = check_integrity(file=directory, local_path=target / "extracted", client=mock_client)

        assert state == IntegrityState.Incorrect

    def test_incorrect_when_extracted_file_deleted(self, source_zip, target, mock_client):
        directory = self._prepared(source_zip, target)
        (target / "extracted" / "root" / "subdir" / "file2.txt").unlink()

        state = check_integrity(file=directory, local_path=target / "extracted", client=mock_client)

        assert state == IntegrityState.Incorrect

    def test_ignores_files_the_spec_excludes(self, source_zip, target, mock_client):
        """A file outside the include patterns is not extracted, so its absence is not a defect."""
        directory = self._prepared(source_zip, target, include_patterns=["root/file1.txt"])

        state = check_integrity(file=directory, local_path=target / "extracted", client=mock_client)

        assert state == IntegrityState.Correct
        assert not (target / "extracted" / "root" / "subdir" / "file2.txt").exists()

    def test_incorrect_when_cache_archive_missing(self, source_zip, target, mock_client):
        directory = self._prepared(source_zip, target)
        (target / "extracted.zip").unlink()

        state = check_integrity(file=directory, local_path=target / "extracted", client=mock_client)

        assert state == IntegrityState.Incorrect

    def test_incorrect_when_cache_archive_stale(self, source_zip, target, mock_client):
        directory = self._prepared(source_zip, target)
        with zipfile.ZipFile(target / "extracted.zip", "w") as zip_file:
            zip_file.writestr("root/file1.txt", "content1")

        state = check_integrity(file=directory, local_path=target / "extracted", client=mock_client)

        assert state == IntegrityState.Incorrect

    def test_incorrect_when_cache_archive_is_not_a_zip(self, source_zip, target, mock_client):
        """A checksum-matching resource that isn't an archive must report a state, not raise."""
        directory = self._prepared(source_zip, target)
        not_a_zip = target / "extracted.zip"
        _ = not_a_zip.write_text("this is not a zip file")
        directory = directory.model_copy(update={"checksum": md5_checksum(not_a_zip)})

        state = check_integrity(file=directory, local_path=target / "extracted", client=mock_client)

        assert state == IntegrityState.Incorrect

    def test_missing_when_directory_absent(self, source_zip, target, mock_client):
        directory = ResolvedDirectory(
            source=FileSourceLocal(local=str(source_zip)),
            filename="extracted",
            extract="zip",
            checksum=md5_checksum(source_zip),
        )

        state = check_integrity(file=directory, local_path=target / "extracted", client=mock_client)

        assert state == IntegrityState.Missing

    def test_incorrect_when_directory_empty(self, source_zip, target, mock_client):
        directory = ResolvedDirectory(
            source=FileSourceLocal(local=str(source_zip)),
            filename="extracted",
            extract="zip",
            checksum=md5_checksum(source_zip),
        )
        (target / "extracted").mkdir(parents=True)

        state = check_integrity(file=directory, local_path=target / "extracted", client=mock_client)

        assert state == IntegrityState.Incorrect

    def test_not_checked_without_checksum(self, source_zip, target, mock_client):
        directory = ResolvedDirectory(
            source=FileSourceLocal(local=str(source_zip)),
            filename="extracted",
            extract="zip",
            checksum=None,
        )
        prepare_resolved_directory(directory, target, PrepareContext())

        state = check_integrity(file=directory, local_path=target / "extracted", client=mock_client)

        assert state == IntegrityState.NotChecked

    def test_incorrect_when_path_is_a_file(self, source_zip, target, mock_client):
        directory = ResolvedDirectory(
            source=FileSourceLocal(local=str(source_zip)),
            filename="extracted",
            extract="zip",
            checksum=md5_checksum(source_zip),
        )
        target.mkdir()
        _ = Path(target / "extracted").write_text("not a directory")

        state = check_integrity(file=directory, local_path=target / "extracted", client=mock_client)

        assert state == IntegrityState.Incorrect

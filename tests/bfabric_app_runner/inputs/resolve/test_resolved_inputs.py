import pytest
from pydantic import ValidationError
from bfabric_app_runner.inputs.resolve.resolved_inputs import (
    ResolvedInputs,
    ResolvedFile,
    ResolvedStaticFile,
    ResolvedDirectory,
)
from bfabric_app_runner.specs.inputs.file_spec import FileSourceLocal


class TestResolvedInputsValidation:
    """Test the validation logic in ResolvedInputs.no_duplicates."""

    def test_no_duplicates_valid_single_file(self):
        """Test that a single file passes validation."""
        inputs = ResolvedInputs(
            files=[
                ResolvedFile(
                    filename="test.txt",
                    source=FileSourceLocal(local="/test.txt"),
                    link=False,
                    checksum=None,
                )
            ]
        )
        # Should not raise an exception
        assert len(inputs.files) == 1

    def test_no_duplicates_valid_multiple_files(self):
        """Test that multiple files with different names pass validation."""
        inputs = ResolvedInputs(
            files=[
                ResolvedFile(
                    filename="file1.txt",
                    source=FileSourceLocal(local="/file1.txt"),
                    link=False,
                    checksum=None,
                ),
                ResolvedStaticFile(
                    filename="file2.txt",
                    content="content",
                ),
                ResolvedDirectory(
                    filename="mydir",
                    source=FileSourceLocal(local="/mydir.zip"),
                    extract="zip",
                ),
            ]
        )
        # Should not raise an exception
        assert len(inputs.files) == 3

    def test_no_duplicates_exact_duplicate_filenames(self):
        """Test that exact duplicate filenames are rejected."""
        with pytest.raises(ValidationError, match="Duplicate filenames in resolved inputs: test.txt"):
            ResolvedInputs(
                files=[
                    ResolvedFile(
                        filename="test.txt",
                        source=FileSourceLocal(local="/test1.txt"),
                        link=False,
                        checksum=None,
                    ),
                    ResolvedFile(
                        filename="test.txt",
                        source=FileSourceLocal(local="/test2.txt"),
                        link=False,
                        checksum=None,
                    ),
                ]
            )

    def test_no_duplicates_multiple_exact_duplicates(self):
        """Test that multiple sets of duplicates are reported."""
        with pytest.raises(ValidationError, match="Duplicate filenames in resolved inputs: file1.txt, file2.txt"):
            ResolvedInputs(
                files=[
                    ResolvedFile(
                        filename="file1.txt", source=FileSourceLocal(local="/f1a.txt"), link=False, checksum=None
                    ),
                    ResolvedFile(
                        filename="file1.txt", source=FileSourceLocal(local="/f1b.txt"), link=False, checksum=None
                    ),
                    ResolvedFile(
                        filename="file2.txt", source=FileSourceLocal(local="/f2a.txt"), link=False, checksum=None
                    ),
                    ResolvedFile(
                        filename="file2.txt", source=FileSourceLocal(local="/f2b.txt"), link=False, checksum=None
                    ),
                ]
            )

    def test_current_directory_alone_valid(self):
        """Test that current directory '.' alone is valid."""
        inputs = ResolvedInputs(
            files=[
                ResolvedDirectory(
                    filename=".",
                    source=FileSourceLocal(local="/archive.zip"),
                    extract="zip",
                )
            ]
        )
        # Should not raise an exception
        assert len(inputs.files) == 1

    def test_current_directory_with_other_files_invalid(self):
        """Test that current directory '.' cannot coexist with other files."""
        with pytest.raises(ValidationError, match="Current directory '.' cannot coexist with other files"):
            ResolvedInputs(
                files=[
                    ResolvedDirectory(
                        filename=".",
                        source=FileSourceLocal(local="/archive.zip"),
                        extract="zip",
                    ),
                    ResolvedFile(
                        filename="test.txt",
                        source=FileSourceLocal(local="/test.txt"),
                        link=False,
                        checksum=None,
                    ),
                ]
            )

    def test_directory_file_conflict_simple(self):
        """Test that directory conflicts with files inside it."""
        with pytest.raises(ValidationError, match=r"Path 'mydir/file\.txt' conflicts with directory 'mydir'"):
            ResolvedInputs(
                files=[
                    ResolvedDirectory(
                        filename="mydir",
                        source=FileSourceLocal(local="/mydir.zip"),
                        extract="zip",
                    ),
                    ResolvedFile(
                        filename="mydir/file.txt",
                        source=FileSourceLocal(local="/file.txt"),
                        link=False,
                        checksum=None,
                    ),
                ]
            )

    def test_directory_file_conflict_nested(self):
        """Test that directory conflicts with deeply nested files."""
        with pytest.raises(ValidationError, match=r"Path 'mydir/subdir/file\.txt' conflicts with directory 'mydir'"):
            ResolvedInputs(
                files=[
                    ResolvedDirectory(
                        filename="mydir",
                        source=FileSourceLocal(local="/mydir.zip"),
                        extract="zip",
                    ),
                    ResolvedFile(
                        filename="mydir/subdir/file.txt",
                        source=FileSourceLocal(local="/file.txt"),
                        link=False,
                        checksum=None,
                    ),
                ]
            )

    def test_file_directory_conflict_parent(self):
        """Test that file conflicts with directory that would be its parent."""
        with pytest.raises(ValidationError, match=r"Path 'mydir/file\.txt' conflicts with directory 'mydir'"):
            ResolvedInputs(
                files=[
                    ResolvedFile(
                        filename="mydir/file.txt",
                        source=FileSourceLocal(local="/file.txt"),
                        link=False,
                        checksum=None,
                    ),
                    ResolvedDirectory(
                        filename="mydir",
                        source=FileSourceLocal(local="/mydir.zip"),
                        extract="zip",
                    ),
                ]
            )

    def test_file_directory_conflict_grandparent(self):
        """Test that file conflicts with directory that would be its grandparent."""
        with pytest.raises(ValidationError, match=r"Path 'mydir/subdir/file\.txt' conflicts with directory 'mydir'"):
            ResolvedInputs(
                files=[
                    ResolvedFile(
                        filename="mydir/subdir/file.txt",
                        source=FileSourceLocal(local="/file.txt"),
                        link=False,
                        checksum=None,
                    ),
                    ResolvedDirectory(
                        filename="mydir",
                        source=FileSourceLocal(local="/mydir.zip"),
                        extract="zip",
                    ),
                ]
            )

    def test_no_conflict_sibling_directories(self):
        """Test that sibling directories don't conflict."""
        inputs = ResolvedInputs(
            files=[
                ResolvedDirectory(
                    filename="dir1",
                    source=FileSourceLocal(local="/dir1.zip"),
                    extract="zip",
                ),
                ResolvedDirectory(
                    filename="dir2",
                    source=FileSourceLocal(local="/dir2.zip"),
                    extract="zip",
                ),
            ]
        )
        # Should not raise an exception
        assert len(inputs.files) == 2

    def test_no_conflict_sibling_files(self):
        """Test that sibling files don't conflict."""
        inputs = ResolvedInputs(
            files=[
                ResolvedFile(
                    filename="dir1/file.txt",
                    source=FileSourceLocal(local="/file1.txt"),
                    link=False,
                    checksum=None,
                ),
                ResolvedFile(
                    filename="dir2/file.txt",
                    source=FileSourceLocal(local="/file2.txt"),
                    link=False,
                    checksum=None,
                ),
            ]
        )
        # Should not raise an exception
        assert len(inputs.files) == 2

    def test_no_conflict_directory_and_unrelated_file(self):
        """Test that directory and unrelated file don't conflict."""
        inputs = ResolvedInputs(
            files=[
                ResolvedDirectory(
                    filename="mydir",
                    source=FileSourceLocal(local="/mydir.zip"),
                    extract="zip",
                ),
                ResolvedFile(
                    filename="otherfile.txt",
                    source=FileSourceLocal(local="/other.txt"),
                    link=False,
                    checksum=None,
                ),
            ]
        )
        # Should not raise an exception
        assert len(inputs.files) == 2

    def test_mixed_file_types_no_conflict(self):
        """Test that all file types can coexist without conflicts."""
        inputs = ResolvedInputs(
            files=[
                ResolvedFile(
                    filename="data/input.txt",
                    source=FileSourceLocal(local="/input.txt"),
                    link=False,
                    checksum=None,
                ),
                ResolvedStaticFile(
                    filename="config/settings.json",
                    content='{"setting": "value"}',
                ),
                ResolvedDirectory(
                    filename="archive",
                    source=FileSourceLocal(local="/archive.zip"),
                    extract="zip",
                ),
            ]
        )
        # Should not raise an exception
        assert len(inputs.files) == 3


class TestResolvedInputsApplyFilter:
    """Test the apply_filter method."""

    def test_apply_filter_keeps_matching_files(self):
        """Test that apply_filter keeps only files in the filter list."""
        inputs = ResolvedInputs(
            files=[
                ResolvedFile(
                    filename="file1.txt",
                    source=FileSourceLocal(local="/file1.txt"),
                    link=False,
                    checksum=None,
                ),
                ResolvedFile(
                    filename="file2.txt",
                    source=FileSourceLocal(local="/file2.txt"),
                    link=False,
                    checksum=None,
                ),
                ResolvedFile(
                    filename="file3.txt",
                    source=FileSourceLocal(local="/file3.txt"),
                    link=False,
                    checksum=None,
                ),
            ]
        )

        filtered = inputs.apply_filter(["file1.txt", "file3.txt"])
        assert len(filtered.files) == 2
        assert {f.filename for f in filtered.files} == {"file1.txt", "file3.txt"}

    def test_apply_filter_empty_filter(self):
        """Test that apply_filter with empty filter returns empty result."""
        inputs = ResolvedInputs(
            files=[
                ResolvedFile(
                    filename="file1.txt",
                    source=FileSourceLocal(local="/file1.txt"),
                    link=False,
                    checksum=None,
                ),
            ]
        )

        filtered = inputs.apply_filter([])
        assert len(filtered.files) == 0

    def test_apply_filter_no_matches(self):
        """Test that apply_filter with no matches returns empty result."""
        inputs = ResolvedInputs(
            files=[
                ResolvedFile(
                    filename="file1.txt",
                    source=FileSourceLocal(local="/file1.txt"),
                    link=False,
                    checksum=None,
                ),
            ]
        )

        filtered = inputs.apply_filter(["nonexistent.txt"])
        assert len(filtered.files) == 0

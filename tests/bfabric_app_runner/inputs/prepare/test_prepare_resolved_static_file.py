from pathlib import Path

import pytest
from bfabric_app_runner.inputs.prepare.prepare_resolved_static_file import (
    prepare_resolved_static_file,
    _write_file_if_changed,
)


@pytest.fixture
def mock_logger(mocker):
    return mocker.patch("bfabric_app_runner.inputs.prepare.prepare_resolved_static_file.logger")


class MockResolvedStaticFile:
    def __init__(self, filename, content):
        self.filename = filename
        self.content = content


def test_prepare_resolved_static_file(fs, mock_logger):
    # Setup working directory in fake filesystem
    working_dir = Path("/working/dir")

    # Create a test file
    file = MockResolvedStaticFile(filename="test.txt", content="test content")

    # Call the function
    prepare_resolved_static_file(file=file, working_dir=working_dir)

    # Verify the directory was created
    assert working_dir.exists()

    # Verify the file was created with correct content
    output_file = working_dir / "test.txt"
    assert output_file.exists()
    assert output_file.read_text() == "test content"
    mock_logger.info.assert_called_once_with(f"Writen to {output_file}")


def test_prepare_resolved_static_file_nested_path(fs, mock_logger):
    # Setup working directory in fake filesystem
    working_dir = Path("/working/dir")

    # Create a test file with a nested path
    file = MockResolvedStaticFile(filename="nested/path/test.txt", content="test content")

    # Call the function
    prepare_resolved_static_file(file=file, working_dir=working_dir)

    # Verify the nested directories were created
    nested_dir = working_dir / "nested" / "path"
    assert nested_dir.exists()

    # Verify the file was created with correct content
    output_file = nested_dir / "test.txt"
    assert output_file.exists()
    assert output_file.read_text() == "test content"
    mock_logger.info.assert_called_once_with(f"Writen to {output_file}")


def test_write_file_if_changed_file_does_not_exist(fs, mock_logger):
    # Setup path in fake filesystem
    path = Path("/test/file.txt")
    path.parent.mkdir(parents=True, exist_ok=True)

    content = "test content"

    # Call the function
    _write_file_if_changed(content=content, path=path)

    # Verify the file was created with correct content
    assert path.exists()
    assert path.read_text() == content
    mock_logger.info.assert_called_once_with(f"Writen to {path}")


def test_write_file_if_changed_file_exists_with_same_content(fs, mock_logger):
    # Setup existing file in fake filesystem
    path = Path("/test/file.txt")
    path.parent.mkdir(parents=True, exist_ok=True)

    content = "existing content"
    fs.create_file(path, contents=content)

    # Call the function with the same content
    _write_file_if_changed(content=content, path=path)

    # Verify the file wasn't modified
    assert path.exists()
    assert path.read_text() == content
    mock_logger.debug.assert_called_once_with(f"Skipping {path} as it already exists and has the same content")
    mock_logger.info.assert_not_called()


def test_write_file_if_changed_file_exists_with_different_content(fs, mock_logger):
    # Setup existing file in fake filesystem
    path = Path("/test/file.txt")
    path.parent.mkdir(parents=True, exist_ok=True)

    existing_content = "existing content"
    fs.create_file(path, contents=existing_content)

    # Record the original modification time
    original_mtime = path.stat().st_mtime

    # Call the function with different content
    new_content = "new content"
    _write_file_if_changed(content=new_content, path=path)

    # Verify the file was updated with new content
    assert path.exists()
    assert path.read_text() == new_content

    # Verify modification time changed
    assert path.stat().st_mtime > original_mtime

    mock_logger.info.assert_called_once_with(f"Writen to {path}")


def test_write_file_if_changed_path_exists_but_not_file(fs):
    # Setup existing directory (not file) in fake filesystem
    path = Path("/test/dir")
    path.mkdir(parents=True, exist_ok=True)

    content = "test content"

    # Call the function should raise ValueError
    with pytest.raises(ValueError, match=f"Path {path} exists but is not a file"):
        _write_file_if_changed(content=content, path=path)


def test_write_file_if_changed_binary_content(fs, mock_logger):
    # Setup path in fake filesystem
    path = Path("/test/file.bin")
    path.parent.mkdir(parents=True, exist_ok=True)

    content = b"binary content"

    # Call the function
    _write_file_if_changed(content=content, path=path)

    # Verify the file was created with correct content
    assert path.exists()
    assert path.read_bytes() == content
    mock_logger.info.assert_called_once_with(f"Writen to {path}")


def test_write_file_if_changed_binary_content_same_content(fs, mock_logger):
    # Setup existing file in fake filesystem
    path = Path("/test/file.bin")
    path.parent.mkdir(parents=True, exist_ok=True)

    content = b"binary content"
    fs.create_file(path, contents=content)

    # Call the function with the same content
    _write_file_if_changed(content=content, path=path)

    # Verify the file wasn't modified
    assert path.exists()
    assert path.read_bytes() == content
    mock_logger.debug.assert_called_once_with(f"Skipping {path} as it already exists and has the same content")
    mock_logger.info.assert_not_called()

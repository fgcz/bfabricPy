import datetime
from pathlib import Path

import pytest

from bfabric_scripts.feeder.file_attributes import FileAttributes


@pytest.fixture
def fake_file(fs):
    """Fixture to create a fake file for testing."""
    file_path = Path("/test/root/my/test_file.txt")
    fs.create_file(file_path, contents=b"Test content")
    return file_path


def test_compute(fake_file):
    attributes = FileAttributes.compute(file=fake_file)
    assert attributes.md5_checksum == "8bfa8e0684108f419933a5995264d150"
    assert isinstance(attributes.file_date, datetime.datetime)
    assert attributes.file_size == 12
    assert attributes.filename == "test_file.txt"

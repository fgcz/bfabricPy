from pathlib import Path

import pytest

from bfabric.entities import Resource


@pytest.fixture
def data_dict():
    return {
        "id": 1,
        "name": "mismatched.txt",
        "storage": {"classname": "storage", "id": 2, "basepath": "/test/storage"},
        "relativepath": "path/to/resource.txt",
    }


@pytest.fixture()
def resource(data_dict, mock_client, bfabric_instance):
    return Resource(data_dict, client=mock_client, bfabric_instance=bfabric_instance)


def test_storage_relative_path(resource):
    assert resource.storage_relative_path == Path("path/to/resource.txt")


@pytest.mark.parametrize(
    "storage_path,resource_path",
    [
        ("/test/storage/", "path/to/resource.txt"),
        ("/test/storage/", "/path/to/resource.txt"),
        ("/test/storage", "path/to/resource.txt"),
        ("/test/storage", "/path/to/resource.txt"),
    ],
)
def test_storage_absolute_path(resource, storage_path, resource_path):
    resource._Entity__data_dict["relativepath"] = resource_path
    assert resource.storage_absolute_path == Path("/test/storage/path/to/resource.txt")


def test_filename(resource):
    assert resource.filename == "resource.txt"

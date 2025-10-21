from pathlib import Path

import pytest

from bfabric.entities import Resource, Storage


@pytest.fixture
def data_dict():
    return {
        "id": 1,
        "name": "mismatched.txt",
        "storage": {"classname": "storage", "id": 2},
        "relativepath": "path/to/resource.txt",
    }


@pytest.fixture()
def resource(data_dict):
    return Resource(data_dict)


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
def test_storage_absolute_path(mocker, data_dict, storage_path, resource_path):
    data_dict["relativepath"] = resource_path
    resource = Resource(data_dict)
    mocker.patch.object(Storage, "find").return_value.base_path = storage_path
    assert resource.storage_absolute_path == Path("/test/storage/path/to/resource.txt")


def test_filename(resource):
    assert resource.filename == "resource.txt"

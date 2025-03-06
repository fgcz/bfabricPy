import pytest
from bfabric_app_runner.inputs.resolve._resolve_bfabric_resource_specs import ResolveBfabricResourceSpecs
from bfabric_app_runner.specs.inputs.file_spec import FileSpec

from bfabric.entities import Resource, Storage


@pytest.fixture
def mock_client(mocker):
    return mocker.MagicMock(name="mock_client")


@pytest.fixture
def resolver(mock_client):
    return ResolveBfabricResourceSpecs(mock_client)


def test_call(resolver, mocker, mock_client):
    # Setup mock resources and storages
    mock_resource = {"storage": {"id": 1}, "relativepath": "/path/to/file.txt", "filechecksum": "abc123"}

    mock_storage = {"host": "example.com", "basepath": "/data"}

    # Mock Resource.find_all to return our mock resource
    mocker.patch.object(Resource, "find_all", return_value={42: mock_resource})

    # Mock Storage.find_all to return our mock storage
    mocker.patch.object(Storage, "find_all", return_value={1: mock_storage})

    # Create mock spec
    mock_spec = mocker.MagicMock(name="mock_spec")
    mock_spec.id = 42
    mock_spec.filename = "renamed_file.txt"
    mock_spec.check_checksum = True

    # Call the function under test
    result = resolver([mock_spec])

    # Assert the results
    assert len(result) == 1
    assert isinstance(result[0], FileSpec)
    assert result[0].filename == "renamed_file.txt"
    assert result[0].link is False
    assert result[0].checksum == "abc123"
    assert result[0].source.ssh.host == "example.com"
    assert result[0].source.ssh.path == "/data/path/to/file.txt"

    # Verify the correct methods were called
    Resource.find_all.assert_called_once_with(ids=[42], client=mock_client)
    Storage.find_all.assert_called_once_with(ids=[1], client=mock_client)


def test_call_when_empty(resolver):
    specs = []
    result = resolver(specs)
    assert result == []


def test_call_multiple_resources(resolver, mocker, mock_client):
    # Setup mock resources and storages
    mock_resources = {
        101: {"storage": {"id": 1}, "relativepath": "/path/to/file1.txt", "filechecksum": "abc123"},
        102: {"storage": {"id": 2}, "relativepath": "/path/to/file2.txt", "filechecksum": "def456"},
    }

    mock_storages = {
        1: {"host": "example.com", "basepath": "/data1"},
        2: {"host": "example2.com", "basepath": "/data2"},
    }

    # Mock find_all methods
    mocker.patch.object(Resource, "find_all", return_value=mock_resources)
    mocker.patch.object(Storage, "find_all", return_value=mock_storages)

    # Create mock specs
    mock_spec1 = mocker.MagicMock(name="mock_spec1")
    mock_spec1.id = 101
    mock_spec1.filename = "renamed_file1.txt"
    mock_spec1.check_checksum = True

    mock_spec2 = mocker.MagicMock(name="mock_spec2")
    mock_spec2.id = 102
    mock_spec2.filename = None
    mock_spec2.check_checksum = False

    # Call the function under test
    result = resolver([mock_spec1, mock_spec2])

    # Assert the results
    assert len(result) == 2

    # First file spec
    assert result[0].filename == "renamed_file1.txt"
    assert result[0].checksum == "abc123"
    assert result[0].source.ssh.host == "example.com"
    assert result[0].source.ssh.path == "/data1/path/to/file1.txt"

    # Second file spec
    assert result[1].filename == "file2.txt"  # Should use basename from relativepath
    assert result[1].checksum is None  # Should be None since check_checksum is False
    assert result[1].source.ssh.host == "example2.com"
    assert result[1].source.ssh.path == "/data2/path/to/file2.txt"


def test_get_file_spec(resolver, mocker):
    # Setup test data
    mock_spec = mocker.MagicMock(name="mock_spec")
    mock_spec.filename = "custom_name.txt"
    mock_spec.check_checksum = True

    mock_resource = {"relativepath": "/path/to/original.txt", "filechecksum": "abc123"}

    mock_storage = {"host": "example.com", "basepath": "/data"}

    # Call the method under test
    result = resolver._get_file_spec(spec=mock_spec, resource=mock_resource, storage=mock_storage)

    # Assert the result
    assert isinstance(result, FileSpec)
    assert result.filename == "custom_name.txt"
    assert result.link is False
    assert result.checksum == "abc123"
    assert result.source.ssh.host == "example.com"
    assert result.source.ssh.path == "/data/path/to/original.txt"


def test_get_file_spec_no_filename(resolver, mocker):
    # Setup test data
    mock_spec = mocker.MagicMock(name="mock_spec")
    mock_spec.filename = None
    mock_spec.check_checksum = False

    mock_resource = {"relativepath": "/path/to/original.txt", "filechecksum": "abc123"}

    mock_storage = {"host": "example.com", "basepath": "/data"}

    # Call the method under test
    result = resolver._get_file_spec(spec=mock_spec, resource=mock_resource, storage=mock_storage)

    # Assert the result
    assert result.filename == "original.txt"  # Should use basename
    assert result.checksum is None  # Should be None since check_checksum is False

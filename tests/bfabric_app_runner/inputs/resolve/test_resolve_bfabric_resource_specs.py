from pathlib import Path

import pytest
from bfabric_app_runner.inputs.resolve._resolve_bfabric_resource_specs import ResolveBfabricResourceSpecs
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedFile

from bfabric.entities import Resource
from bfabric.entities.core.uri import EntityUri


def _resource_uri(resource_id: int) -> EntityUri:
    return EntityUri(f"https://fgcz-bfabric.uzh.ch/bfabric/resource/show.html?id={resource_id}")


@pytest.fixture
def mock_client(mocker):
    return mocker.MagicMock(name="mock_client")


@pytest.fixture
def resolver(mock_client):
    return ResolveBfabricResourceSpecs(mock_client)


def test_call(resolver, mocker, mock_client):
    # Setup mock resources and storages
    mock_storage = {"host": "example.com", "basepath": "/data"}
    mock_resource = mocker.MagicMock(
        name="mock_resource",
        storage=mock_storage,
        storage_absolute_path="/data/path/to/file.txt",
        spec=["storage", "storage_absolute_path", "__getitem__"],
    )
    mock_resource.__getitem__.side_effect = lambda key: {"filechecksum": "abc123"}[key]

    # Mock reader.read_ids to return our mock resource keyed by URI
    mock_client.reader.read_ids.return_value = {_resource_uri(42): mock_resource}

    # Create mock spec
    mock_spec = mocker.MagicMock(name="mock_spec", id=42, filename="renamed_file.txt", check_checksum=True)

    # Call the function under test
    result = resolver([mock_spec])

    # Assert the results
    assert len(result) == 1
    assert isinstance(result[0], ResolvedFile)
    assert result[0].filename == "renamed_file.txt"
    assert result[0].link is False
    assert result[0].checksum == "abc123"
    assert result[0].source.ssh.host == "example.com"
    assert result[0].source.ssh.path == "/data/path/to/file.txt"

    # Verify the correct methods were called
    mock_client.reader.read_ids.assert_called_once_with(Resource, [42])


def test_call_when_empty(resolver):
    specs = []
    result = resolver(specs)
    assert result == []


def test_call_multiple_resources(resolver, mocker, mock_client):
    # Setup mock resources and storages
    mock_storages = {
        1: {"host": "example.com", "basepath": "/data1"},
        2: {"host": "example2.com", "basepath": "/data2"},
    }
    mock_resources = {
        101: mocker.MagicMock(
            name="mock_resources[101]",
            storage=mock_storages[1],
            storage_absolute_path="/data1/path/to/file1.txt",
            filename="file1.txt",
            spec=["storage", "storage_absolute_path", "filename", "__getitem__"],
        ),
        102: mocker.MagicMock(
            name="mock_resources[102]",
            storage=mock_storages[2],
            storage_absolute_path="/data2/path/to/file2.txt",
            filename="file2.txt",
            spec=["storage", "storage_absolute_path", "filename", "__getitem__"],
        ),
    }
    mock_resources[101].__getitem__.side_effect = lambda key: {"filechecksum": "abc123"}[key]
    mock_resources[102].__getitem__.side_effect = lambda key: {"filechecksum": "def456"}[key]

    # Mock reader.read_ids to return the resources keyed by URI
    mock_client.reader.read_ids.return_value = {
        _resource_uri(resource_id): resource for resource_id, resource in mock_resources.items()
    }

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


def test_call_when_resource_missing_raises_key_error(resolver, mocker, mock_client):
    """A not-found resource is None in read_ids' result and filtered out on re-key, so indexing it by
    id raises KeyError downstream (matching the previous find_all behavior of dropping misses)."""
    mock_resource = mocker.MagicMock(
        name="mock_resource",
        storage={"host": "example.com", "basepath": "/data"},
        storage_absolute_path="/data/path/to/file.txt",
        spec=["storage", "storage_absolute_path", "__getitem__"],
    )
    mock_resource.__getitem__.side_effect = lambda key: {"filechecksum": "abc123"}[key]
    # id=101 found, id=102 missing (None)
    mock_client.reader.read_ids.return_value = {_resource_uri(101): mock_resource, _resource_uri(102): None}

    spec_found = mocker.MagicMock(name="spec_found", id=101, filename="found.txt", check_checksum=True)
    spec_missing = mocker.MagicMock(name="spec_missing", id=102, filename="missing.txt", check_checksum=True)

    with pytest.raises(KeyError):
        resolver([spec_found, spec_missing])


def test_get_file_spec(resolver, mocker):
    # Setup test data
    mock_spec = mocker.MagicMock(name="mock_spec")
    mock_spec.filename = "custom_name.txt"
    mock_spec.check_checksum = True

    mock_storage = {"host": "example.com", "basepath": "/data"}
    mock_resource = mocker.MagicMock(
        name="mock_resource",
        storage=mock_storage,
        storage_absolute_path="/data/path/to/original.txt",
        spec=["storage", "storage_absolute_path", "filename", "__getitem__"],
    )
    mock_resource.__getitem__.side_effect = lambda key: {"filechecksum": "abc123"}[key]

    # Call the method under test
    result = resolver._get_file_spec(spec=mock_spec, resource=mock_resource)

    # Assert the result
    assert isinstance(result, ResolvedFile)
    assert result.filename == "custom_name.txt"
    assert result.link is False
    assert result.checksum == "abc123"
    assert result.source.ssh.host == "example.com"
    assert result.source.ssh.path == "/data/path/to/original.txt"


def test_get_file_spec_http_access(resolver, mocker, mock_client):
    mock_spec = mocker.MagicMock(name="mock_spec")
    mock_spec.access = "http"
    mock_spec.filename = "renamed.txt"
    mock_spec.check_checksum = True

    mock_storage = mocker.MagicMock(name="mock_storage", id=7)
    mock_resource = mocker.MagicMock(name="mock_resource", storage=mock_storage)
    mock_resource.storage_relative_path = Path("path/to/original.txt")
    mock_resource.__getitem__.side_effect = lambda key: {"filechecksum": "abc123"}[key]

    mock_client.read.return_value = [{"protocol": "https", "host": "trace.example.com", "basepath": "/data/"}]

    result = resolver._get_file_spec(spec=mock_spec, resource=mock_resource)

    mock_client.read.assert_called_once_with("access", {"storageid": 7, "type": "HTTP"})
    assert result.filename == "renamed.txt"
    assert result.checksum == "abc123"
    assert result.source.http.url == "https://trace.example.com/data/path/to/original.txt"
    assert result.source.http.auth == "bfabric"


def test_get_file_spec_http_access_no_records_raises(resolver, mocker, mock_client):
    mock_spec = mocker.MagicMock(name="mock_spec")
    mock_spec.access = "http"
    mock_spec.filename = "renamed.txt"
    mock_spec.check_checksum = True

    mock_storage = mocker.MagicMock(name="mock_storage", id=7)
    mock_resource = mocker.MagicMock(name="mock_resource", storage=mock_storage, id=99)
    mock_resource.__getitem__.side_effect = lambda key: {"filechecksum": "abc123"}[key]

    mock_client.read.return_value = []

    with pytest.raises(ValueError, match="no HTTP access configured"):
        resolver._get_file_spec(spec=mock_spec, resource=mock_resource)


def test_get_file_spec_no_filename(resolver, mocker):
    # Setup test data
    mock_spec = mocker.MagicMock(name="mock_spec")
    mock_spec.filename = None
    mock_spec.check_checksum = False

    mock_storage = {"host": "example.com", "basepath": "/data"}
    mock_resource = mocker.MagicMock(
        name="mock_resource",
        storage=mock_storage,
        storage_absolute_path="/data/path/to/original.txt",
        filename="original.txt",
        spec=["storage", "storage_absolute_path", "filename", "__getitem__"],
    )
    mock_resource.__getitem__.side_effect = lambda key: {"filechecksum": "abc123"}[key]

    # Call the method under test
    result = resolver._get_file_spec(spec=mock_spec, resource=mock_resource)

    # Assert the result
    assert result.filename == "original.txt"  # Should use basename
    assert result.checksum is None  # Should be None since check_checksum is False

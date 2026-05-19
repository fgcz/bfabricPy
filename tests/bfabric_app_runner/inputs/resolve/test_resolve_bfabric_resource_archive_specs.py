from pathlib import PosixPath

import pytest

from bfabric.entities.core.uri import EntityUri
from bfabric_app_runner.inputs.resolve._resolve_bfabric_resource_archive_specs import ResolveBfabricResourceArchiveSpecs
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedDirectory
from bfabric_app_runner.specs.inputs.bfabric_resource_archive_spec import BfabricResourceArchiveSpec


@pytest.fixture
def mock_client(mocker):
    return mocker.MagicMock(name="mock_client")


@pytest.fixture
def resolver(mock_client):
    return ResolveBfabricResourceArchiveSpecs(mock_client)


@pytest.fixture
def mock_storage(mocker):
    storage = mocker.MagicMock(name="mock_storage")
    storage.__getitem__ = mocker.MagicMock(side_effect=lambda key: {"host": "example.com"}[key])
    return storage


def test_get_file_source_with_posixpath(resolver, mocker, mock_storage):
    """Regression test: storage_absolute_path is a PosixPath, not a str."""
    mock_resource = mocker.MagicMock(name="mock_resource")
    mock_resource.storage_absolute_path = PosixPath("/srv/www/htdocs/xyz.zip")

    result = ResolveBfabricResourceArchiveSpecs._get_file_source(resource=mock_resource, storage=mock_storage)

    assert result.ssh.host == "example.com"
    assert result.ssh.path == "/srv/www/htdocs/xyz.zip"


def test_call_with_posixpath_storage_path(resolver, mocker, mock_client, mock_storage):
    """Integration test: full call path when storage_absolute_path is a PosixPath."""
    storage_uri = EntityUri("https://fgcz-bfabric.uzh.ch/bfabric/storage/show.html?id=1")
    resource_uri = EntityUri("https://fgcz-bfabric.uzh.ch/bfabric/resource/show.html?id=42")

    mock_resource = mocker.MagicMock(name="mock_resource")
    mock_resource.id = 42
    mock_resource.storage_absolute_path = PosixPath("/srv/www/htdocs/xyz.zip")
    mock_resource.refs.uris = {"storage": storage_uri}
    mock_resource.__getitem__ = mocker.MagicMock(side_effect=lambda key: {"filechecksum": "abc123"}[key])

    mock_client.reader.read_ids.return_value = {resource_uri: mock_resource}
    mock_client.reader.read_uris.return_value = {storage_uri: mock_storage}

    spec = BfabricResourceArchiveSpec(id=42, filename="output_dir")
    result = resolver([spec])

    assert len(result) == 1
    assert isinstance(result[0], ResolvedDirectory)
    assert result[0].source.ssh.host == "example.com"
    assert result[0].source.ssh.path == "/srv/www/htdocs/xyz.zip"
    assert result[0].filename == "output_dir"

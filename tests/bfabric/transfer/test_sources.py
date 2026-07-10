from __future__ import annotations

from pathlib import Path

import pytest

from bfabric.transfer import TransferSourceHttp, TransferSourceSsh
from bfabric.transfer.sources import http_source, resource_sources, ssh_source


def test_ssh_source(mocker):
    resource = mocker.MagicMock()
    resource.storage = {"host": "example.com"}
    resource.storage_absolute_path = "/data/path/to/file.txt"

    result = ssh_source(resource)

    assert result == TransferSourceSsh(host="example.com", path="/data/path/to/file.txt")


def test_http_source(mocker):
    resource = mocker.MagicMock()
    resource.storage = mocker.MagicMock(id=7)
    resource.storage_relative_path = Path("path/to/original.txt")
    client = mocker.MagicMock()
    client.read.return_value = [{"protocol": "https", "host": "trace.example.com", "basepath": "/data/"}]

    result = http_source(resource, client)

    assert result == TransferSourceHttp(url="https://trace.example.com/data/path/to/original.txt", auth="bfabric")
    client.read.assert_called_once_with("access", {"storageid": 7, "type": "HTTP"})


def test_http_source_no_records_raises(mocker):
    resource = mocker.MagicMock()
    resource.storage = mocker.MagicMock(id=7)
    resource.storage_relative_path = Path("path/to/original.txt")
    client = mocker.MagicMock()
    client.read.return_value = []

    with pytest.raises(ValueError, match="no HTTP access"):
        http_source(resource, client)


def _combined_resource(mocker):
    """A resource that both ssh_source (dict-style storage) and http_source (storage.id) can consume."""
    resource = mocker.MagicMock()
    storage = mocker.MagicMock(id=7)
    storage.__getitem__.side_effect = {"host": "example.com"}.__getitem__
    resource.storage = storage
    resource.storage_absolute_path = "/data/path/to/file.txt"
    resource.storage_relative_path = Path("path/to/original.txt")
    return resource


def test_resource_sources_ssh_only_needs_no_client(mocker):
    resource = mocker.MagicMock()
    resource.storage = {"host": "example.com"}
    resource.storage_absolute_path = "/data/path/to/file.txt"

    result = resource_sources(resource, allow={"ssh"})

    assert result == [TransferSourceSsh(host="example.com", path="/data/path/to/file.txt")]


def test_resource_sources_http_requires_client(mocker):
    resource = _combined_resource(mocker)

    with pytest.raises(ValueError, match="client is required"):
        resource_sources(resource, client=None, allow={"http"})


def test_resource_sources_default_returns_ssh_then_http(mocker):
    resource = _combined_resource(mocker)
    client = mocker.MagicMock()
    client.read.return_value = [{"protocol": "https", "host": "trace.example.com", "basepath": "/data/"}]

    result = resource_sources(resource, client=client)

    assert [source.type for source in result] == ["ssh", "http"]
    assert result[0] == TransferSourceSsh(host="example.com", path="/data/path/to/file.txt")
    assert result[1] == TransferSourceHttp(url="https://trace.example.com/data/path/to/original.txt", auth="bfabric")


def test_resource_sources_empty_allow_raises(mocker):
    resource = _combined_resource(mocker)

    with pytest.raises(ValueError):
        resource_sources(resource, allow=set())

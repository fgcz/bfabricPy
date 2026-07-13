from __future__ import annotations

from pathlib import Path

import pytest

from bfabric.transfer import TransferSourceHttp, TransferSourceSsh
from bfabric.transfer.sources import http_source, ssh_source


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

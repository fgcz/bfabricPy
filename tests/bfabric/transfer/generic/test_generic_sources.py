from __future__ import annotations

from pathlib import Path

from pydantic import TypeAdapter

from bfabric.transfer._generic.sources import (
    TransferSource,
    TransferSourceHttp,
    TransferSourceLocal,
    TransferSourceSsh,
)


def test_local_construct_and_default_type():
    source = TransferSourceLocal(path=Path("/data/file.txt"))
    assert source.type == "local"
    assert source.path == Path("/data/file.txt")


def test_ssh_construct_and_default_type():
    source = TransferSourceSsh(host="host", path="/data/file.txt")
    assert source.type == "ssh"
    assert source.host == "host"
    assert source.path == "/data/file.txt"


def test_http_construct_and_defaults():
    source = TransferSourceHttp(url="https://host/data/f.txt")
    assert source.type == "http"
    assert source.url == "https://host/data/f.txt"
    assert source.auth is None


def test_http_auth_bfabric():
    source = TransferSourceHttp(url="https://host/data/f.txt", auth="bfabric")
    assert source.auth == "bfabric"


def test_discriminated_union_validates_http():
    source = TypeAdapter(TransferSource).validate_python({"type": "http", "url": "https://host/data/f.txt"})
    assert isinstance(source, TransferSourceHttp)
    assert source.url == "https://host/data/f.txt"


def test_discriminated_union_validates_local():
    source = TypeAdapter(TransferSource).validate_python({"type": "local", "path": "/data/file.txt"})
    assert isinstance(source, TransferSourceLocal)
    assert source.path == Path("/data/file.txt")


def test_discriminated_union_validates_ssh():
    source = TypeAdapter(TransferSource).validate_python({"type": "ssh", "host": "host", "path": "/data/file.txt"})
    assert isinstance(source, TransferSourceSsh)
    assert source.host == "host"
    assert source.path == "/data/file.txt"

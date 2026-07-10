from __future__ import annotations

from pathlib import Path

from bfabric.transfer._generic.sinks import (
    TransferSink,
    TransferSinkLocal,
    TransferSinkScp,
    TransferSinkTus,
)
from pydantic import TypeAdapter

_adapter = TypeAdapter(TransferSink)


def test_sink_type_discriminators():
    assert TransferSinkLocal(path=Path("/x")).type == "local"
    assert TransferSinkScp(host="h", path="/x").type == "scp"
    assert TransferSinkTus(endpoint="https://t/", metadata={}, token="tok").type == "tus"


def test_sink_union_validates_from_dicts():
    assert _adapter.validate_python({"type": "local", "path": "/x"}) == TransferSinkLocal(path=Path("/x"))
    assert _adapter.validate_python({"type": "scp", "host": "h", "path": "/x"}) == TransferSinkScp(host="h", path="/x")
    tus = _adapter.validate_python(
        {"type": "tus", "endpoint": "https://t/", "metadata": {"resourceId": "1"}, "token": "tok"}
    )
    assert tus == TransferSinkTus(endpoint="https://t/", metadata={"resourceId": "1"}, token="tok")

from __future__ import annotations

import base64
import json

import pytest


@pytest.fixture
def make_jwt():
    """Factory building a fake (unsigned) 3-segment JWT string carrying ``payload`` as its claims."""

    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    def _make(payload: object) -> str:
        header = _b64url(json.dumps({"alg": "none"}).encode("utf-8"))
        body = _b64url(json.dumps(payload).encode("utf-8"))
        return f"{header}.{body}.sig"

    return _make

"""Unit tests for the BfabricAuthMiddleware unauthenticated_paths allowlist."""

from __future__ import annotations

import re
from typing import Any

import pytest

from bfabric_asgi_auth.middleware import BfabricAuthMiddleware
from bfabric_asgi_auth.token_validation.mock_strategy import create_mock_validator


class _RecordingApp:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        self.calls.append(scope)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})


class _Capture:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def __call__(self, event: dict) -> None:
        self.events.append(event)


async def _noop_receive() -> dict:
    return {"type": "http.request"}


def _scope(path: str) -> dict:
    return {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "session": {},
    }


@pytest.mark.asyncio
async def test_unauthenticated_string_path_bypasses_session_check() -> None:
    app = _RecordingApp()
    middleware = BfabricAuthMiddleware(
        app=app,
        token_validator=create_mock_validator(),
        unauthenticated_paths=["/health"],
    )
    capture = _Capture()
    await middleware(_scope("/health"), _noop_receive, capture)
    assert len(app.calls) == 1
    assert capture.events[0]["status"] == 200


@pytest.mark.asyncio
async def test_unauthenticated_regex_path_bypasses_session_check() -> None:
    app = _RecordingApp()
    middleware = BfabricAuthMiddleware(
        app=app,
        token_validator=create_mock_validator(),
        unauthenticated_paths=[re.compile(r"/static/.*")],
    )
    capture = _Capture()
    await middleware(_scope("/static/main.css"), _noop_receive, capture)
    assert len(app.calls) == 1


@pytest.mark.asyncio
async def test_non_matching_path_still_rejected() -> None:
    app = _RecordingApp()
    middleware = BfabricAuthMiddleware(
        app=app,
        token_validator=create_mock_validator(),
        unauthenticated_paths=["/health"],
    )
    capture = _Capture()
    await middleware(_scope("/private"), _noop_receive, capture)
    assert app.calls == []
    assert capture.events[0]["status"] == 401


@pytest.mark.asyncio
async def test_default_no_allowlist_rejects_everything() -> None:
    app = _RecordingApp()
    middleware = BfabricAuthMiddleware(app=app, token_validator=create_mock_validator())
    capture = _Capture()
    await middleware(_scope("/health"), _noop_receive, capture)
    assert app.calls == []
    assert capture.events[0]["status"] == 401


@pytest.mark.asyncio
async def test_unauthenticated_path_respects_root_path_stripping() -> None:
    app = _RecordingApp()
    middleware = BfabricAuthMiddleware(
        app=app,
        token_validator=create_mock_validator(),
        unauthenticated_paths=["/health"],
    )
    scope = _scope("/zip/health")
    scope["root_path"] = "/zip"
    capture = _Capture()
    await middleware(scope, _noop_receive, capture)
    assert len(app.calls) == 1

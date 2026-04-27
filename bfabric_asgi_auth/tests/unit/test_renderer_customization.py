"""Unit tests for HTMLRenderer / PlainTextRenderer customization knobs."""

from __future__ import annotations

import pytest

from bfabric_asgi_auth.response_renderer import (
    ErrorResponse,
    HTMLRenderer,
    PlainTextRenderer,
    RedirectResponse,
)


class _Capture:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def __call__(self, event: dict) -> None:
        self.events.append(event)


def _scope() -> dict:
    return {"type": "http", "headers": [], "root_path": "", "method": "GET", "path": "/"}


@pytest.mark.asyncio
async def test_redirect_status_default_is_303() -> None:
    capture = _Capture()
    await HTMLRenderer().render_redirect(RedirectResponse("/", "authenticated"), _scope(), None, capture)  # type: ignore[arg-type]
    assert capture.events[0]["status"] == 303


@pytest.mark.asyncio
async def test_redirect_status_overridable() -> None:
    capture = _Capture()
    renderer = HTMLRenderer(redirect_status=307)
    await renderer.render_redirect(RedirectResponse("/", "authenticated"), _scope(), None, capture)  # type: ignore[arg-type]
    assert capture.events[0]["status"] == 307


@pytest.mark.asyncio
async def test_plaintext_renderer_redirect_status_overridable() -> None:
    capture = _Capture()
    renderer = PlainTextRenderer(redirect_status=302)
    await renderer.render_redirect(RedirectResponse("/", "authenticated"), _scope(), None, capture)  # type: ignore[arg-type]
    assert capture.events[0]["status"] == 302


@pytest.mark.asyncio
async def test_error_message_hook_receives_error_type_and_default() -> None:
    seen: list[tuple[str, str]] = []

    def hook(error_type: str, default: str) -> str:
        seen.append((error_type, default))
        return f"CUSTOM[{error_type}]"

    capture = _Capture()
    renderer = HTMLRenderer(error_message=hook)
    response = ErrorResponse.invalid_token(error_kind="expired")
    await renderer.render_error(response, _scope(), None, capture)  # type: ignore[arg-type]

    assert seen == [("token_expired", response.message)]
    body = b"".join(e.get("body", b"") for e in capture.events).decode()
    assert "CUSTOM[token_expired]" in body


@pytest.mark.asyncio
async def test_error_title_hook_receives_status_code_and_default() -> None:
    seen: list[tuple[str, int, str]] = []

    def hook(error_type: str, status_code: int, default: str) -> str:
        seen.append((error_type, status_code, default))
        return f"TITLE[{error_type}]"

    capture = _Capture()
    renderer = HTMLRenderer(error_title=hook)
    response = ErrorResponse.unauthorized()
    await renderer.render_error(response, _scope(), None, capture)  # type: ignore[arg-type]

    assert seen == [("unauthorized", 401, "Unauthorized")]
    body = b"".join(e.get("body", b"") for e in capture.events).decode()
    assert "TITLE[unauthorized]" in body


@pytest.mark.asyncio
async def test_bfabric_branding_default_renders_wordmark_and_footer() -> None:
    capture = _Capture()
    await HTMLRenderer().render_error(ErrorResponse.unauthorized(), _scope(), None, capture)  # type: ignore[arg-type]
    body = b"".join(e.get("body", b"") for e in capture.events).decode()
    assert "B-FABRIC" in body
    assert "Return to B-Fabric" in body


@pytest.mark.asyncio
async def test_bfabric_branding_disabled_omits_branding() -> None:
    capture = _Capture()
    await HTMLRenderer(bfabric_branding=False).render_error(
        ErrorResponse.unauthorized(), _scope(), None, capture
    )  # type: ignore[arg-type]
    body = b"".join(e.get("body", b"") for e in capture.events).decode()
    assert "B-FABRIC" not in body
    assert "Return to B-Fabric" not in body


@pytest.mark.asyncio
async def test_bfabric_url_renders_link_in_default_footer() -> None:
    capture = _Capture()
    renderer = HTMLRenderer(bfabric_url="https://fgcz-bfabric.uzh.ch/bfabric/")
    await renderer.render_error(ErrorResponse.unauthorized(), _scope(), None, capture)  # type: ignore[arg-type]
    body = b"".join(e.get("body", b"") for e in capture.events).decode()
    assert 'href="https://fgcz-bfabric.uzh.ch/bfabric/"' in body


@pytest.mark.asyncio
async def test_back_link_renders() -> None:
    capture = _Capture()
    renderer = HTMLRenderer(back_link=("/launch", "Launch from B-Fabric"))
    await renderer.render_error(ErrorResponse.unauthorized(), _scope(), None, capture)  # type: ignore[arg-type]
    body = b"".join(e.get("body", b"") for e in capture.events).decode()
    assert 'href="/launch"' in body
    assert "Launch from B-Fabric" in body


@pytest.mark.asyncio
async def test_custom_logo_html_overrides_default() -> None:
    capture = _Capture()
    renderer = HTMLRenderer(logo_html='<img src="/logo.svg">')
    await renderer.render_error(ErrorResponse.unauthorized(), _scope(), None, capture)  # type: ignore[arg-type]
    body = b"".join(e.get("body", b"") for e in capture.events).decode()
    assert '<img src="/logo.svg">' in body
    assert "B-FABRIC" not in body

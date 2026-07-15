"""OAuth 2.0 Authorization Code flow with PKCE for interactive CLI login.

Implements the browser-based login flow:

1. Start a local HTTP server to receive the authorization callback
2. Open the authorization URL in the user's browser
3. Exchange the authorization code for tokens via the token endpoint

No extra dependencies — uses stdlib ``http.server``, ``webbrowser``,
``secrets``, ``hashlib``; plus ``httpx`` (already a project dependency).
"""

from __future__ import annotations

import base64
import hashlib
import html
import secrets
import sys
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from loguru import logger

from bfabric.errors import BfabricOAuthError


def _generate_verifier(length: int = 128) -> str:
    """Generate a PKCE code verifier (RFC 7636 Section 4.1).

    Returns a URL-safe string of the requested *length* (43..128 chars).
    """
    if not (43 <= length <= 128):
        raise ValueError(f"PKCE verifier length must be 43..128, got {length}")
    # token_urlsafe produces ~4/3 * nbytes chars; generate enough then truncate.
    return secrets.token_urlsafe(96)[:length]


def _generate_challenge(verifier: str) -> str:
    """Derive the S256 code challenge from *verifier* (RFC 7636 Section 4.2).

    Returns base64url(SHA-256(verifier)) without ``=`` padding.
    """
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


@dataclass
class _AuthorizationResult:
    """Holds the query parameters received on the OAuth redirect."""

    code: str | None = None
    state: str | None = None
    error: str | None = None
    error_description: str | None = None


_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
          margin: 0; min-height: 100vh; display: flex;
          align-items: center; justify-content: center; background: #f5f5f7; }}
  .card {{ max-width: 28rem; padding: 2.5rem 3rem; text-align: center;
           background: #fff; border-radius: 12px;
           box-shadow: 0 4px 24px rgba(0,0,0,.08); }}
  .icon {{ font-size: 3rem; line-height: 1; color: {accent}; }}
  h1 {{ margin: .75rem 0 .5rem; font-size: 1.4rem; color: {accent}; }}
  p {{ margin: .25rem 0; color: #555; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: #1c1c1e; }} .card {{ background: #2c2c2e; box-shadow: none; }}
    p {{ color: #aaa; }}
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    <h1>{title}</h1>
    {body}
  </div>
</body>
</html>"""


def _render_callback_page(result: _AuthorizationResult) -> bytes:
    """Build the HTML page shown in the browser after the OAuth redirect.

    No auto-close / close button: browsers only let scripts close windows they
    opened themselves, so ``window.close()`` is a no-op for this browser-navigated
    tab. We just tell the user they can close it.
    """
    if result.error is not None or result.code is None:
        accent, icon, title = "#cf222e", "✕", "Login failed"
        detail = result.error_description or result.error or "No authorization code was received."
        body = f"<p>{html.escape(detail)}</p><p>You can close this tab and return to your terminal.</p>"
    else:
        accent, icon, title = "#1a7f37", "✓", "Login successful"
        body = "<p>You can close this tab and return to your terminal.</p>"
    return _PAGE_TEMPLATE.format(accent=accent, icon=icon, title=title, body=body).encode("utf-8")


class _CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler that captures the OAuth authorization callback."""

    server: _CallbackServer  # pyright: ignore[reportIncompatibleVariableOverride]

    def do_GET(self) -> None:  # noqa: N802
        qs = parse_qs(urlparse(self.path).query)
        result = _AuthorizationResult(
            code=qs.get("code", [None])[0],
            state=qs.get("state", [None])[0],
            error=qs.get("error", [None])[0],
            error_description=qs.get("error_description", [None])[0],
        )
        self.server.result = result

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        _ = self.wfile.write(_render_callback_page(result))

        # Shut down the server from a daemon thread so this handler can return.
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002  # pyright: ignore[reportImplicitOverride]
        """Suppress default stderr logging."""


class _CallbackServer(HTTPServer):
    """Local HTTP server that listens for the OAuth redirect callback."""

    result: _AuthorizationResult

    def __init__(self, port: int = 0) -> None:
        super().__init__(("127.0.0.1", port), _CallbackHandler)
        self.result = _AuthorizationResult()

    @property
    def redirect_uri(self) -> str:
        """The redirect URI that should be registered with the authorization server."""
        return f"http://127.0.0.1:{self.server_address[1]}/callback"


def _exchange_code(
    *,
    token_url: str,
    client_id: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> dict[str, object]:
    """Exchange an authorization code for tokens at the token endpoint."""
    response = httpx.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
        timeout=30,
    )
    _ = response.raise_for_status()
    result: dict[str, object] = response.json()  # pyright: ignore[reportAny]
    return result


def pkce_login(
    base_url: str,
    *,
    client_id: str,
    scope: str,
    port: int = 0,
    open_browser: bool = True,
    timeout: float = 120.0,
) -> dict[str, object]:
    """Perform an OAuth 2.0 Authorization Code flow with PKCE.

    Opens the user's browser to the B-Fabric authorization endpoint,
    waits for the redirect callback on a local HTTP server, then
    exchanges the authorization code for tokens.

    :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
    :param client_id: OAuth client ID
    :param scope: OAuth scope
    :param port: Local port for the callback server (``0`` = auto-assign)
    :param open_browser: Whether to open the authorization URL in the browser.
        If ``False`` (or if the browser fails to open), the URL is printed to stderr.
    :param timeout: Seconds to wait for the user to complete login
    :returns: Token dict with ``access_token``, ``refresh_token``, etc.
    :raises RuntimeError: On timeout, CSRF state mismatch, or authorization error
    """
    base_url = base_url.rstrip("/")
    logger.debug("Starting PKCE login flow for {}", base_url)
    verifier = _generate_verifier()
    challenge = _generate_challenge(verifier)
    state = secrets.token_urlsafe(32)

    server = _CallbackServer(port)

    authorize_url = f"{base_url}/rest/oauth/authorize?" + urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": server.redirect_uri,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "scope": scope,
        }
    )

    # Try to open the browser; fall back to printing the URL.
    browser_opened = False
    if open_browser:
        browser_opened = webbrowser.open(authorize_url)
    if not browser_opened:
        print(f"Open this URL to log in:\n{authorize_url}", file=sys.stderr)

    # Run the server in a daemon thread and wait for the callback.
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    server_thread.join(timeout=timeout)

    if server_thread.is_alive():
        server.shutdown()
        raise BfabricOAuthError(f"PKCE login timed out after {timeout} seconds")

    result = server.result

    # Validate CSRF state.
    if result.state != state:
        logger.debug("CSRF state mismatch: expected {!r}, got {!r}", state, result.state)
        raise BfabricOAuthError("CSRF state mismatch in OAuth callback")

    # Check for authorization errors.
    if result.error is not None:
        msg = f"Authorization error: {result.error}"
        if result.error_description:
            msg += f" — {result.error_description}"
        raise BfabricOAuthError(msg)

    if result.code is None:
        raise BfabricOAuthError("No authorization code received")

    # Exchange the code for tokens.
    logger.debug("Exchanging authorization code for tokens")
    token_url = f"{base_url}/rest/oauth/token"
    return _exchange_code(
        token_url=token_url,
        client_id=client_id,
        code=result.code,
        redirect_uri=server.redirect_uri,
        code_verifier=verifier,
    )

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
import secrets
import sys
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

if TYPE_CHECKING:
    pass


def _generate_verifier(length: int = 128) -> str:
    """Generate a PKCE code verifier (RFC 7636 Section 4.1).

    Returns a URL-safe string of the requested *length* (43..128 chars).
    """
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


class _CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler that captures the OAuth authorization callback."""

    server: _CallbackServer  # type: ignore[assignment]

    def do_GET(self) -> None:  # noqa: N802
        qs = parse_qs(urlparse(self.path).query)
        self.server.result = _AuthorizationResult(
            code=qs.get("code", [None])[0],
            state=qs.get("state", [None])[0],
            error=qs.get("error", [None])[0],
            error_description=qs.get("error_description", [None])[0],
        )

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Login successful</h1>"
            b"<p>You can close this tab.</p></body></html>"
        )

        # Shut down the server from a daemon thread so this handler can return.
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
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
    )
    response.raise_for_status()
    return response.json()  # pyright: ignore[reportReturnType]


def pkce_login(
    base_url: str,
    *,
    client_id: str = "bfabric-cli",
    scope: str = "api:read api:write",
    port: int = 0,
    open_browser: bool = True,
    timeout: float = 120.0,
) -> dict[str, object]:
    """Perform an OAuth 2.0 Authorization Code flow with PKCE.

    Opens the user's browser to the B-Fabric authorization endpoint,
    waits for the redirect callback on a local HTTP server, then
    exchanges the authorization code for tokens.

    :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
    :param client_id: OAuth client ID (default ``"bfabric-cli"``)
    :param scope: OAuth scope (default ``"api:read api:write"``)
    :param port: Local port for the callback server (``0`` = auto-assign)
    :param open_browser: Whether to open the authorization URL in the browser.
        If ``False`` (or if the browser fails to open), the URL is printed to stderr.
    :param timeout: Seconds to wait for the user to complete login
    :returns: Token dict with ``access_token``, ``refresh_token``, etc.
    :raises RuntimeError: On timeout, CSRF state mismatch, or authorization error
    """
    base_url = base_url.rstrip("/")
    verifier = _generate_verifier()
    challenge = _generate_challenge(verifier)
    state = secrets.token_urlsafe(32)

    server = _CallbackServer(port)

    authorize_url = f"{base_url}/rest/oauth/authorize?" + urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": server.redirect_uri,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "scope": scope,
    })

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
        raise RuntimeError(f"PKCE login timed out after {timeout} seconds")

    result = server.result

    # Validate CSRF state.
    if result.state != state:
        raise RuntimeError(
            f"CSRF state mismatch: expected {state!r}, got {result.state!r}"
        )

    # Check for authorization errors.
    if result.error is not None:
        msg = f"Authorization error: {result.error}"
        if result.error_description:
            msg += f" — {result.error_description}"
        raise RuntimeError(msg)

    if result.code is None:
        raise RuntimeError("No authorization code received")

    # Exchange the code for tokens.
    token_url = f"{base_url}/rest/oauth/token"
    return _exchange_code(
        token_url=token_url,
        client_id=client_id,
        code=result.code,
        redirect_uri=server.redirect_uri,
        code_verifier=verifier,
    )

"""OAuth 2.0 Device Authorization Grant (RFC 8628) for headless/SSH login.

Implements the device code flow:

1. Request a device code + user code from the authorization server
2. Display the user code and verification URI to the user
3. Poll the token endpoint until the user authorizes or the request expires

No extra dependencies — uses ``httpx`` (already a project dependency),
``time``, and ``sys``.
"""

from __future__ import annotations

import sys
import time

import httpx


def _request_device_code(
    base_url: str,
    *,
    client_id: str,
    scope: str,
) -> dict[str, object]:
    """Request a device code from the authorization server.

    Posts to ``{base_url}/rest/oauth/device_authorization`` with the
    given *client_id* and *scope*.

    :returns: Dict with ``device_code``, ``user_code``, ``verification_uri``,
        optionally ``verification_uri_complete``, ``expires_in``, ``interval``.
    :raises httpx.HTTPStatusError: On non-2xx responses
    """
    response = httpx.post(
        f"{base_url}/rest/oauth/device_authorization",
        data={
            "client_id": client_id,
            "scope": scope,
        },
    )
    response.raise_for_status()
    return response.json()  # pyright: ignore[reportReturnType]


def _poll_for_token(
    base_url: str,
    *,
    device_code: str,
    client_id: str,
    interval: float,
    timeout: float,
) -> dict[str, object]:
    """Poll the token endpoint until the user authorizes the device.

    Implements the polling loop described in RFC 8628 Section 3.5:

    - ``authorization_pending`` — sleep and retry
    - ``slow_down`` — increase interval by 5 seconds, sleep and retry
    - ``expired_token`` — raise ``RuntimeError``
    - ``access_denied`` — raise ``RuntimeError``

    :returns: Token dict with ``access_token``, ``refresh_token``, etc.
    :raises RuntimeError: On timeout, expired token, or access denied
    """
    token_url = f"{base_url}/rest/oauth/token"
    deadline = time.monotonic() + timeout
    poll_interval = interval

    while True:
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Device code login timed out after {timeout} seconds")

        try:
            response = httpx.post(
                token_url,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": device_code,
                    "client_id": client_id,
                },
            )
        except httpx.TransportError:
            # Network-level errors (connection refused, DNS, etc.) — retry
            time.sleep(poll_interval)
            continue

        if response.status_code == 200:
            return response.json()  # pyright: ignore[reportReturnType]

        # Transient server errors — retry instead of crashing
        if response.status_code >= 500:
            time.sleep(poll_interval)
            continue

        # Token endpoint returns 400 with an error code for pending/slow_down/etc.
        try:
            error_body = response.json()
        except Exception:
            response.raise_for_status()
            raise RuntimeError(f"Unexpected response: {response.status_code}")  # pragma: no cover

        error = error_body.get("error", "")

        if error == "authorization_pending":
            time.sleep(poll_interval)
            continue

        if error == "slow_down":
            poll_interval += 5
            time.sleep(poll_interval)
            continue

        if error == "expired_token":
            raise RuntimeError("Device code expired before user authorized")

        if error == "access_denied":
            raise RuntimeError("User denied the authorization request")

        # Unknown error — raise with whatever info we have
        description = error_body.get("error_description", "")
        msg = f"Device code token error: {error}"
        if description:
            msg += f" — {description}"
        raise RuntimeError(msg)


def device_code_login(
    base_url: str,
    *,
    client_id: str = "bfabric-cli",
    scope: str = "api:read api:write",
    timeout: float = 600.0,
) -> dict[str, object]:
    """Perform an OAuth 2.0 Device Authorization Grant flow (RFC 8628).

    Requests a device code, displays the user code and verification URI,
    then polls until the user authorizes or the request times out.

    :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
    :param client_id: OAuth client ID (default ``"bfabric-cli"``)
    :param scope: OAuth scope (default ``"api:read api:write"``)
    :param timeout: Seconds to wait for the user to authorize (default 600)
    :returns: Token dict with ``access_token``, ``refresh_token``, etc.
    :raises RuntimeError: On timeout, expired token, or access denied
    """
    base_url = base_url.rstrip("/")
    device_response = _request_device_code(base_url, client_id=client_id, scope=scope)

    user_code = device_response["user_code"]
    verification_uri = device_response["verification_uri"]
    verification_uri_complete = device_response.get("verification_uri_complete")
    interval = float(device_response.get("interval", 5))

    print(f"To authorize, visit: {verification_uri}", file=sys.stderr)
    print(f"and enter code: {user_code}", file=sys.stderr)
    if verification_uri_complete:
        print(f"Or open: {verification_uri_complete}", file=sys.stderr)

    return _poll_for_token(
        base_url,
        device_code=str(device_response["device_code"]),
        client_id=client_id,
        interval=interval,
        timeout=timeout,
    )

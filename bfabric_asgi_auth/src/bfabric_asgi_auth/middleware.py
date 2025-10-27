from __future__ import annotations

import re
from urllib.parse import parse_qs

from asgiref.typing import ASGIReceiveCallable, ASGISendCallable, Scope

from bfabric_asgi_auth.session_data import SessionData, SessionState
from bfabric_asgi_auth.session_store import SessionStoreMem
from bfabric_asgi_auth.token_validator import TokenValidator


class BfabricAuthMiddleware:
    """ASGI middleware for Bfabric authentication using URL-based sessions."""

    def __init__(
        self,
        app,
        token_validator: TokenValidator,
        session_store: SessionStoreMem | None = None,
        landing_path: str = "/landing",
        session_prefix: str = "/session",
        token_param: str = "token",
    ) -> None:
        """Initialize the middleware.

        :param app: The ASGI application to wrap
        :param token_validator: Token validator instance
        :param session_store: Session store (creates new one if not provided)
        :param landing_path: URL path for landing page (default: /landing)
        :param session_prefix: URL prefix for session paths (default: /session)
        :param token_param: Query parameter name for token (default: token)
        """
        self.app = app
        self.token_validator = token_validator
        self.session_store = session_store or SessionStoreMem()
        self.landing_path = landing_path
        self.session_prefix = session_prefix
        self.token_param = token_param

        # Compile regex for session URL matching: /session/{uuid}/...
        self.session_pattern = re.compile(
            rf"^{re.escape(session_prefix)}/([0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}})(/.*)?$"
        )

    async def __call__(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        # Only process HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]

        # Handle landing URL with token
        if path == self.landing_path:
            await self._handle_landing(scope, receive, send)
            return

        # Handle session URLs
        match = self.session_pattern.match(path)
        if match:
            session_id = match.group(1)
            remaining_path = match.group(2) or "/"
            await self._handle_session(scope, receive, send, session_id, remaining_path)
            return

        # Unauthorized access
        await self._send_unauthorized(send)

    async def _handle_landing(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        """Handle landing page request with token."""
        # Parse query string
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token = params.get(self.token_param, [None])[0]

        if not token:
            await self._send_error(send, "Missing token parameter")
            return

        # Validate token
        result = await self.token_validator.validate(token)

        if not result.success:
            await self._send_error(send, result.error or "Token validation failed")
            return

        # Create new session
        session_data = SessionData(
            state=SessionState.NEW,
            token=token,
            client_config=result.client_config,
            user_info=result.user_info,
        )

        # Update to READY state (in a real app, this might be async initialization)
        session_data = session_data.update_ready(
            client_config=result.client_config or {},
            user_info=result.user_info,
        )

        session_id = self.session_store.create(session_data.model_dump())

        # Redirect to session URL
        redirect_url = f"{self.session_prefix}/{session_id}/"
        await self._send_redirect(send, redirect_url)

    async def _handle_session(
        self,
        scope: Scope,
        receive: ASGIReceiveCallable,
        send: ASGISendCallable,
        session_id: str,
        remaining_path: str,
    ) -> None:
        """Handle session-authenticated request."""
        # Get session data
        session_data_dict = self.session_store.get(session_id)

        if not session_data_dict:
            await self._send_unauthorized(send, "Session not found or expired")
            return

        # Parse session data
        session_data = SessionData(**session_data_dict)

        if session_data.state == SessionState.ERROR:
            await self._send_error(send, session_data.error or "Session error")
            return

        if session_data.state != SessionState.READY:
            await self._send_error(send, "Session not ready")
            return

        # Attach session data to scope
        scope["session_id"] = session_id
        scope["session_data"] = session_data_dict
        scope["bfabric_connection"] = session_data.client_config

        # Rewrite path to remove session prefix
        scope["path"] = remaining_path

        # Pass to the main application
        await self.app(scope, receive, send)

    async def _send_redirect(self, send: ASGISendCallable, location: str) -> None:
        """Send HTTP redirect response."""
        await send(
            {
                "type": "http.response.start",
                "status": 302,
                "headers": [
                    (b"location", location.encode("utf-8")),
                    (b"content-type", b"text/plain"),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"Redirecting...",
            }
        )

    async def _send_unauthorized(self, send: ASGISendCallable, message: str = "Unauthorized") -> None:
        """Send HTTP 401 response."""
        body = f"{message}\n".encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"text/plain"),
                    (b"content-length", str(len(body)).encode("utf-8")),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )

    async def _send_error(self, send: ASGISendCallable, message: str) -> None:
        """Send HTTP 400 response."""
        body = f"Error: {message}\n".encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 400,
                "headers": [
                    (b"content-type", b"text/plain"),
                    (b"content-length", str(len(body)).encode("utf-8")),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )

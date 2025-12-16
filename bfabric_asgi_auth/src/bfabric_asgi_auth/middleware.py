from __future__ import annotations

from urllib.parse import parse_qs

from asgiref.typing import ASGIReceiveCallable, ASGISendCallable, Scope
from pydantic import SecretStr
from starlette.requests import Request
from starlette.responses import PlainTextResponse, RedirectResponse

from bfabric_asgi_auth.session_data import SessionData
from bfabric_asgi_auth.token_validator import TokenValidatorStrategy


class BfabricAuthMiddleware:
    """ASGI middleware for Bfabric authentication using session cookies.

    This middleware must be added BEFORE SessionMiddleware when using add_middleware()
    (which adds middleware in reverse order), so that SessionMiddleware wraps this middleware.
    """

    def __init__(
        self,
        app,
        token_validator: TokenValidatorStrategy,
        landing_path: str = "/landing",
        token_param: str = "token",
        authenticated_path: str = "/",
        logout_path: str = "/logout",
    ) -> None:
        """Initialize the middleware.

        :param app: The ASGI application to wrap
        :param token_validator: Token validator instance
        :param landing_path: URL path for landing page (default: /landing)
        :param token_param: Query parameter name for token (default: token)
        :param authenticated_path: Path to redirect to after successful authentication (default: /)
        :param logout_path: URL path for logout (default: /logout)
        """
        self.app = app
        self.token_validator = token_validator
        self.landing_path = landing_path
        self.token_param = token_param
        self.authenticated_path = authenticated_path
        self.logout_path = logout_path

    async def __call__(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        # Handle HTTP and WebSocket connections
        if scope["type"] == "http":
            path = scope["path"]

            # Handle logout
            if path == self.logout_path:
                await self._handle_logout(scope, receive, send)
                return

            # Handle landing URL with token
            if path == self.landing_path:
                await self._handle_landing(scope, receive, send)
                return

        # For all other HTTP requests and WebSocket connections, check if session is authenticated
        if scope["type"] in ("http", "websocket"):
            # Get session data from scope (set by SessionMiddleware)
            session = scope.get("session", {})
            session_data_dict = session.get("bfabric_session")

            if not session_data_dict:
                if scope["type"] == "websocket":
                    await self._send_websocket_close(send, 1008, "Not authenticated")
                else:
                    await self._send_unauthorized(send, "Not authenticated")
                return

            # Attach session data to scope for the application
            scope["bfabric_session"] = session_data_dict

        # Pass to the main application
        await self.app(scope, receive, send)

    async def _handle_landing(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        """Handle landing page request with token."""
        # Parse query string
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token_value = params.get(self.token_param, [None])[0]

        if not token_value:
            response = PlainTextResponse("Error: Missing token parameter", status_code=400)
            await response(scope, receive, send)
            return

        token = SecretStr(token_value)

        # Validate token
        result = await self.token_validator(token)

        if not result.success:
            response = PlainTextResponse(f"Error: {result.error or 'Token validation failed'}", status_code=400)
            await response(scope, receive, send)
            return

        # Create session data
        session_data = SessionData(
            client_config=result.client_config or {},
            user_info=result.user_info,
        )

        # Create a Request object to access session properly
        request = Request(scope, receive, send)

        # Store session data using the request's session interface
        # This is the proper way to work with SessionMiddleware
        request.session["bfabric_session"] = session_data.model_dump()

        # Send redirect response
        response = RedirectResponse(url=self.authenticated_path, status_code=302)
        await response(scope, receive, send)

    async def _handle_logout(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        """Handle logout request."""
        # Clear session using Request object
        request = Request(scope, receive, send)
        # Clear the entire session to ensure cookie is removed
        request.session.clear()

        # Send success response
        response = PlainTextResponse("Logged out successfully\n", status_code=200)
        await response(scope, receive, send)

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

    async def _send_websocket_close(self, send: ASGISendCallable, code: int, reason: str) -> None:
        """Close WebSocket connection with error code."""
        await send(
            {
                "type": "websocket.close",
                "code": code,
                "reason": reason,
            }
        )

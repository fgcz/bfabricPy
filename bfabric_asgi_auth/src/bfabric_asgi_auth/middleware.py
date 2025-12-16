from __future__ import annotations

from urllib.parse import parse_qs

from asgiref.typing import ASGI3Application, ASGIReceiveCallable, ASGISendCallable, Scope
from loguru import logger
from pydantic import SecretStr
from starlette.responses import PlainTextResponse, RedirectResponse

from bfabric_asgi_auth.session_data import SessionData
from bfabric_asgi_auth.token_validation.strategy import (
    TokenValidationSuccess,
    TokenValidatorStrategy,
)


class BfabricAuthMiddleware:
    """ASGI middleware for Bfabric authentication using session cookies.

    This middleware must be added BEFORE SessionMiddleware when using add_middleware()
    (which adds middleware in reverse order), so that SessionMiddleware wraps this middleware.
    """

    def __init__(
        self,
        app: ASGI3Application,
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
        self.app: ASGI3Application = app
        self.token_validator: TokenValidatorStrategy = token_validator
        self.landing_path: str = landing_path
        self.token_param: str = token_param
        self.authenticated_path: str = authenticated_path
        self.logout_path: str = logout_path

    async def __call__(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        # Handle middleware-provided operations
        if scope["type"] == "http":
            if scope["path"] == self.logout_path:
                return await self._handle_logout(scope, receive, send)
            if scope["path"] == self.landing_path:
                return await self._handle_landing(scope, receive, send)

        # Ensure authentication is provided
        if scope["type"] == "http" or scope["type"] == "websocket":
            # Get session data from scope (set by SessionMiddleware)
            session = scope.get("session", {})
            session_data_dict = session.get("bfabric_session")

            if not session_data_dict:
                if scope["type"] == "websocket":
                    return await self._send_websocket_close(send, 1008, "Not authenticated")
                else:
                    return await self._send_unauthorized(send, "Not authenticated")

            # Attach session data to scope for the application
            scope["bfabric_session"] = session_data_dict
        elif scope["type"] == "lifespan":
            pass
        else:
            logger.info(f"Dropping unknown scope: {scope['type']}")
            return

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

        if not isinstance(result, TokenValidationSuccess):
            response = PlainTextResponse(f"Error: {result.error or 'Token validation failed'}", status_code=400)
            await response(scope, receive, send)
            return

        # Create session data
        session_data = SessionData(
            bfabric_instance=result.bfabric_instance,
            bfabric_auth_login=result.bfabric_auth.login,
            bfabric_auth_password=result.bfabric_auth.password.get_secret_value(),
            user_info=result.user_info,
        )

        # Store session data by modifying scope["session"] directly
        # This is framework-agnostic and works with any ASGI session middleware
        # that follows the standard pattern (e.g., Starlette, FastAPI, etc.)
        session = scope.get("session")
        if session is None:
            # Session middleware should have set this, but handle gracefully
            response = PlainTextResponse("Error: Session middleware not configured", status_code=500)
            await response(scope, receive, send)
            return

        session["bfabric_session"] = session_data.model_dump()

        # Send redirect response
        response = RedirectResponse(url=self.authenticated_path, status_code=302)
        await response(scope, receive, send)

    async def _handle_logout(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        """Handle logout request."""
        # Clear session by modifying scope["session"] directly
        # This is framework-agnostic and works with any ASGI session middleware
        session = scope.get("session")
        if session is not None:
            session.clear()

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

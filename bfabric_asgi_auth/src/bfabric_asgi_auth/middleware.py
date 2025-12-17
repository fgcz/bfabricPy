from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Protocol, TypeGuard
from urllib.parse import parse_qs

from asgiref.typing import ASGI3Application, ASGIReceiveCallable, ASGISendCallable, Scope
from loguru import logger
from pydantic import SecretStr

from bfabric_asgi_auth.response_renderer import (
    ErrorContext,
    PlainTextRenderer,
    RedirectContext,
    ResponseRenderer,
    SuccessContext,
)
from bfabric_asgi_auth.session_data import SessionData
from bfabric_asgi_auth.token_validation.strategy import (
    TokenValidationSuccess,
    TokenValidatorStrategy,
)

if TYPE_CHECKING:
    from bfabric.rest.token_data import TokenData


JsonRepresentable = str | int | float | bool | None | Mapping[str, "JsonRepresentable"] | Sequence["JsonRepresentable"]


class LandingCallbackProtocol(Protocol):
    async def __call__(self, *, session: dict[str, JsonRepresentable], token_data: TokenData) -> str | None: ...


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
        landing_callback: LandingCallbackProtocol | None = None,
        token_param: str = "token",
        authenticated_path: str = "/",
        logout_path: str = "/logout",
        renderer: ResponseRenderer | None = None,
    ) -> None:
        """Initialize the middleware.

        :param app: The ASGI application to wrap
        :param token_validator: Token validator instance
        :param landing_path: URL path for landing page (default: /landing)
        :param token_param: Query parameter name for token (default: token)
        :param authenticated_path: Path to redirect to after successful authentication (default: /)
        :param logout_path: URL path for logout (default: /logout)
        :param renderer: Response renderer for customizing error/success pages (default: PlainTextRenderer)
        """
        self.app: ASGI3Application = app
        self.token_validator: TokenValidatorStrategy = token_validator
        self.landing_path: str = landing_path
        self.landing_callback: LandingCallbackProtocol | None = landing_callback
        self.token_param: str = token_param
        self.authenticated_path: str = authenticated_path
        self.logout_path: str = logout_path
        self.renderer: ResponseRenderer = renderer or PlainTextRenderer()

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
                    context = ErrorContext(
                        message="Not authenticated",
                        status_code=401,
                        error_type="unauthorized",
                        scope=scope,
                    )
                    return await self.renderer.render_error(context, receive, send)

            # Attach session data to scope for the application
            scope["bfabric_session"] = session_data_dict  # pyright: ignore[reportGeneralTypeIssues]
        elif scope["type"] == "lifespan":
            pass
        else:
            logger.warning(f"Dropping unknown scope: {scope['type']}")  # pyright: ignore[reportUnreachable]
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
            context = ErrorContext(
                message="Missing token parameter",
                status_code=400,
                error_type="missing_token",
                scope=scope,
            )
            await self.renderer.render_error(context, receive, send)
            return

        token = SecretStr(token_value)

        # Validate token
        result = await self.token_validator(token)

        if not isinstance(result, TokenValidationSuccess):
            context = ErrorContext(
                message=result.error or "Token validation failed",
                status_code=400,
                error_type="invalid_token",
                scope=scope,
            )
            await self.renderer.render_error(context, receive, send)
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
            context = ErrorContext(
                message="Session middleware not configured",
                status_code=500,
                error_type="server_error",
                scope=scope,
            )
            await self.renderer.render_error(context, receive, send)
            return
        if not _is_valid_session_dict(session):
            context = ErrorContext(
                message="Invalid session data",
                status_code=400,
                error_type="client_error",
                scope=scope,
            )
            await self.renderer.render_error(context, receive, send)
            return

        # Invoke the landing callback, if configured, and determine the redirect URL
        redirect_url = self.authenticated_path
        if self.landing_callback is not None:
            try:
                callback_result = await self.landing_callback(session=session, token_data=result.token_data)
            except Exception as e:
                logger.error(f"Landing callback failed: {e}")
                context = ErrorContext(
                    message="Landing callback failed",
                    status_code=500,
                    error_type="server_error",
                    scope=scope,
                )
                await self.renderer.render_error(context, receive, send)
                return

            if callback_result is not None:
                redirect_url = callback_result
            else:
                logger.debug("Landing callback returned None, redirecting to default authenticated_path.")

        # update the session
        session["bfabric_session"] = session_data.model_dump()

        # Send redirect response
        context = RedirectContext(url=redirect_url, redirect_type="authenticated", scope=scope)
        await self.renderer.render_redirect(context, receive, send)

    async def _handle_logout(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        """Handle logout request."""
        # Clear session by modifying scope["session"] directly
        # This is framework-agnostic and works with any ASGI session middleware
        session = scope.get("session")
        if session is not None and isinstance(session, dict):
            logged_in = session.get("bfabric_session") is not None  # pyright: ignore[reportUnknownMemberType]
            session.clear()

            # Send success response
            if logged_in:
                context = SuccessContext(message="Logged out successfully", success_type="logout", scope=scope)
                await self.renderer.render_success(context, receive, send)
            else:
                context = ErrorContext(
                    message="User not logged in",
                    status_code=400,
                    error_type="bad_request",
                    scope=scope,
                )
                await self.renderer.render_error(context, receive, send)

    async def _send_websocket_close(self, send: ASGISendCallable, code: int, reason: str) -> None:
        """Close WebSocket connection with error code."""
        await send(
            {
                "type": "websocket.close",
                "code": code,
                "reason": reason,
            }
        )


def _is_json_representable(value: Any) -> TypeGuard[JsonRepresentable]:  # pyright: ignore[reportAny, reportExplicitAny]
    """Check if a value is JSON representable."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return True
    if isinstance(value, dict):
        return all(
            isinstance(k, str) and _is_json_representable(v)
            for k, v in value.items()  # pyright: ignore[reportUnknownVariableType]
        )
    if isinstance(value, list):
        return all(_is_json_representable(item) for item in value)  # pyright: ignore[reportUnknownVariableType]
    return False


def _is_valid_session_dict(
    session: Any,  # pyright: ignore[reportAny, reportExplicitAny]
) -> TypeGuard[dict[str, JsonRepresentable]]:
    """Check if session is a valid dict with string keys and JSON representable values."""
    if not isinstance(session, dict):
        return False
    return all(
        isinstance(key, str) and _is_json_representable(value)
        for key, value in session.items()  # pyright: ignore[reportUnknownVariableType]
    )

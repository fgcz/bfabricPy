from __future__ import annotations

import re
import urllib.parse
from collections.abc import Sequence

from asgiref.typing import ASGI3Application, ASGIReceiveCallable, ASGISendCallable, HTTPScope, Scope, WebSocketScope
from loguru import logger
from pydantic import SecretStr, ValidationError

from bfabric_asgi_auth._root_path import prepend_root_path as _prepend_root_path
from bfabric_asgi_auth._root_path import strip_root_path as _strip_root_path
from bfabric_asgi_auth.response_renderer import (
    ErrorResponse,
    HTMLRenderer,
    RedirectResponse,
    ResponseRenderer,
    SuccessResponse,
    VisibleException,
)
from bfabric_asgi_auth.session_data import SessionData
from bfabric_asgi_auth.token_validation.strategy import (
    TokenValidationSuccess,
    TokenValidatorStrategy,
)
from bfabric_asgi_auth.typing import AuthHooks, is_valid_session_dict
from bfabric_asgi_auth.user import BfabricUser

# Re-exported so existing imports `from bfabric_asgi_auth.middleware import _strip_root_path`
# keep working — the helpers themselves live in ._root_path for use by response_renderer too.
__all__ = ("BfabricAuthMiddleware", "_prepend_root_path", "_strip_root_path")


class BfabricAuthMiddleware:
    """ASGI middleware for Bfabric authentication using session cookies.

    For starlette/fastapi users:
        This middleware must be added BEFORE SessionMiddleware when using add_middleware()
        (which adds middleware in reverse order), so that SessionMiddleware wraps this middleware.
    """

    def __init__(
        self,
        app: ASGI3Application,
        token_validator: TokenValidatorStrategy,
        *,
        landing_path: str = "/landing",
        hooks: AuthHooks | None = None,
        token_param: str = "token",
        authenticated_path: str = "/",
        logout_path: str = "/logout",
        renderer: ResponseRenderer | None = None,
        unauthenticated_paths: Sequence[str | re.Pattern[str]] = (),
    ) -> None:
        """Initialize the middleware.

        :param app: The ASGI application to wrap
        :param token_validator: Token validator instance
        :param landing_path: URL path for landing page (default: /landing)
        :param hooks: Authentication hooks for customizing behavior (default: None)
        :param token_param: Query parameter name for token (default: token)
        :param authenticated_path: Path to redirect to after successful authentication (default: /)
        :param logout_path: URL path for logout (default: /logout)
        :param renderer: Response renderer for customizing error/success pages (default: HTMLRenderer)
        :param unauthenticated_paths: Paths that bypass authentication. Each entry is either a string
            (matched by exact equality on the post-root_path application path) or a compiled
            ``re.Pattern`` (matched with ``fullmatch``). Useful for healthchecks / public assets.
        """
        self.app: ASGI3Application = app
        self.token_validator: TokenValidatorStrategy = token_validator
        self.landing_path: str = landing_path
        self.hooks: AuthHooks | None = hooks
        self.token_param: str = token_param
        self.authenticated_path: str = authenticated_path
        self.logout_path: str = logout_path
        self.renderer: ResponseRenderer = renderer or HTMLRenderer()
        self.unauthenticated_paths: tuple[str | re.Pattern[str], ...] = tuple(unauthenticated_paths)

    async def __call__(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        try:
            # Handle middleware-provided operations
            if scope["type"] == "http":
                app_path = _strip_root_path(scope)
                if app_path == self.logout_path:
                    return await self._handle_logout(scope, receive, send)
                if app_path == self.landing_path:
                    return await self._handle_landing(scope, receive, send)
                if self._is_unauthenticated_path(app_path):
                    return await self.app(scope, receive, send)

            # Ensure authentication is provided
            if scope["type"] == "http" or scope["type"] == "websocket":
                if scope["type"] == "websocket" and self._is_unauthenticated_path(_strip_root_path(scope)):
                    return await self.app(scope, receive, send)
                # Get session data from scope (set by SessionMiddleware)
                session = scope.get("session", {})
                if "bfabric_session" in session:
                    session_data = SessionData.model_validate(session["bfabric_session"])
                    scope["user"] = BfabricUser(session_data)  # pyright: ignore[reportGeneralTypeIssues]
                    return await self.app(scope, receive, send)
                else:
                    return await self._handle_reject(scope=scope, receive=receive, send=send)
            elif scope["type"] == "lifespan":
                return await self.app(scope, receive, send)
            else:
                # We reject unknown scopes, this might need to be extended in the future.
                logger.warning(f"Dropping unknown scope: {scope['type']}")  # pyright: ignore[reportUnreachable]
                return None
        except VisibleException as e:
            logger.exception(f"Error occurred: {e}")
            return await self.renderer.render_error(e.response, scope, receive, send)
        except Exception as e:
            logger.exception(f"Unexpected error occurred: {e}")
            return await self.renderer.render_error(
                ErrorResponse(str(e), status_code=500, error_type="unknown"), scope, receive, send
            )

    def _is_unauthenticated_path(self, app_path: str) -> bool:
        """Return True when the given application path matches an entry in ``unauthenticated_paths``."""
        for entry in self.unauthenticated_paths:
            if isinstance(entry, str):
                if entry == app_path:
                    return True
            elif entry.fullmatch(app_path) is not None:
                return True
        return False

    async def _handle_reject(
        self, scope: HTTPScope | WebSocketScope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        """Handle rejection of authentication.

        For HTTP scopes, the ``on_reject`` hook may return an :class:`ErrorResponse` or
        :class:`RedirectResponse` to override the default 401 page. WebSocket scopes always
        close with code 1008 regardless of hook return value.
        """
        if scope["type"] == "websocket":
            if self.hooks is not None:
                _ = await self.hooks.on_reject(scope=scope)
            return await self._send_websocket_close(send, 1008, "Not authenticated")

        hook_response: ErrorResponse | RedirectResponse | None = None
        if self.hooks is not None:
            hook_response = await self.hooks.on_reject(scope=scope)

        if isinstance(hook_response, RedirectResponse):
            return await self.renderer.render_redirect(hook_response, scope, receive, send)
        if isinstance(hook_response, ErrorResponse):
            return await self.renderer.render_error(hook_response, scope, receive, send)
        return await self.renderer.render_error(ErrorResponse.unauthorized(), scope, receive, send)

    def _get_landing_token(self, scope: Scope) -> SecretStr | None:
        """Get the landing token from the query string."""
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = urllib.parse.parse_qs(query_string)
        token_value = params.get(self.token_param, [None])[0]
        return SecretStr(token_value) if token_value else None

    async def _handle_landing(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        """Handle landing page request with token."""
        # Get the token
        token = self._get_landing_token(scope)
        if not token:
            return await self.renderer.render_error(ErrorResponse.missing_token(), scope, receive, send)

        # Validate the token
        result = await self.token_validator(token)
        if not isinstance(result, TokenValidationSuccess):
            return await self.renderer.render_error(
                ErrorResponse.invalid_token(error_kind=result.error_kind, detail=result.error),
                scope,
                receive,
                send,
            )

        # Create session data
        session_data = SessionData(
            bfabric_instance=result.token_data.caller,
            bfabric_auth_login=result.token_data.user,
            bfabric_auth_password=result.token_data.user_ws_password.get_secret_value(),
            entity_class=result.token_data.entity_class,
            entity_id=result.token_data.entity_id,
            job_id=result.token_data.job_id,
            application_id=result.token_data.application_id,
        )

        # Store session data by modifying scope["session"] directly, this is supported by starlette's SessionMiddleware
        session = scope.get("session")
        if not is_valid_session_dict(session):
            return await self.renderer.render_error(ErrorResponse.invalid_session(), scope, receive, send)

        # If either user or B-Fabric instance is different, evict the session
        try:
            existing_bfabric_session = SessionData.model_validate(session.get("bfabric_session"))
        except ValidationError:
            existing_bfabric_session = None

        if existing_bfabric_session is not None and existing_bfabric_session != session_data:
            session_cleared = False
            if self.hooks:
                session_cleared = await self.hooks.on_evict(session=session)

            if not session_cleared:
                logger.info("Clearing session due to user eviction")
                session.clear()

        # Invoke the landing callback, if configured, and determine the redirect URL
        redirect_url = self.authenticated_path
        if self.hooks is not None:
            callback_result = await self.hooks.on_success(session=session, token_data=result.token_data)

            if callback_result is not None:
                redirect_url = callback_result
                logger.debug(f"Landing callback returned {callback_result}, redirecting.")
            else:
                logger.debug("Landing callback returned None, redirecting to default authenticated_path.")

        # update the session
        session["bfabric_session"] = session_data.model_dump()

        # Send redirect response
        response = RedirectResponse(url=redirect_url, redirect_type="authenticated")
        return await self.renderer.render_redirect(response, scope, receive, send)

    async def _handle_logout(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        """Handle logout request."""
        # Clear session by modifying scope["session"] directly
        # This is framework-agnostic and works with any ASGI session middleware
        session = scope.get("session")
        if session is not None and isinstance(session, dict):
            logged_in = session.get("bfabric_session") is not None  # pyright: ignore[reportUnknownMemberType]
            session.clear()

            if not is_valid_session_dict(session):
                raise ValueError("Invalid session dictionary")

            if self.hooks is not None:
                handled = await self.hooks.on_logout(session=session)
                if handled:
                    return

            # Send success response
            if logged_in:
                await self.renderer.render_success(SuccessResponse.logout(), scope, receive, send)
            else:
                await self.renderer.render_error(ErrorResponse.unauthorized(), scope, receive, send)

    async def _send_websocket_close(self, send: ASGISendCallable, code: int, reason: str) -> None:
        """Close WebSocket connection with error code."""
        await send(
            {
                "type": "websocket.close",
                "code": code,
                "reason": reason,
            }
        )

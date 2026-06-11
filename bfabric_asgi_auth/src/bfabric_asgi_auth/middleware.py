from __future__ import annotations

import urllib.parse
from collections.abc import MutableMapping
from typing import TYPE_CHECKING, Callable

from asgiref.typing import ASGI3Application, ASGIReceiveCallable, ASGISendCallable, HTTPScope, Scope, WebSocketScope
from loguru import logger
from pydantic import SecretStr, ValidationError
from starlette.authentication import BaseUser

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
    TokenValidationError,
    TokenValidationSuccess,
    TokenValidatorStrategy,
)
from bfabric_asgi_auth.typing import AuthHooks, is_valid_session_dict
from bfabric_asgi_auth.user import BfabricUser

if TYPE_CHECKING:
    from bfabric_asgi_auth.token_validation.strategy import TokenValidationResult

# Re-exported so existing imports `from bfabric_asgi_auth.middleware import _strip_root_path`
# keep working — the helpers themselves live in ._root_path for use by response_renderer too.
__all__ = ("BfabricAuthMiddleware", "_prepend_root_path", "_strip_root_path")

# Type aliases for the factory seam.
# SessionFactory: converts a successful validation result to a JSON-serializable dict.
# UserFactory: converts the LIVE mutable session dict to an authenticated user object.
SessionFactory = Callable[["TokenValidationResult"], dict[str, object]]
UserFactory = Callable[[MutableMapping[str, object]], BaseUser]


def _default_session_factory(result: TokenValidationResult) -> dict[str, object]:
    """Legacy SOAP path: build a SessionData dict from TokenValidationSuccess."""
    assert isinstance(result, TokenValidationSuccess), f"Unexpected result type: {type(result)}"
    token_data = result.token_data
    session_data = SessionData(
        bfabric_instance=token_data.caller,
        bfabric_auth_login=token_data.user,
        bfabric_auth_password=token_data.user_ws_password.get_secret_value(),
        entity_class=token_data.entity_class,
        entity_id=token_data.entity_id,
        job_id=token_data.job_id,
        application_id=token_data.application_id,
    )
    return session_data.model_dump()


def _default_user_factory(session_dict: MutableMapping[str, object]) -> BaseUser:
    """Legacy SOAP path: build a BfabricUser from the session dict."""
    return BfabricUser(SessionData.model_validate(dict(session_dict)))


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
        session_factory: SessionFactory | None = None,
        user_factory: UserFactory | None = None,
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
        :param session_factory: Converts a successful validation result to a session dict.
            Defaults to the legacy SOAP path (:class:`SessionData`).
        :param user_factory: Converts the live mutable session dict to a :class:`BaseUser`.
            The factory receives the SAME dict object that is stored in ``scope["session"]``,
            so writing to it during the request persists the change to the cookie on
            ``http.response.start``.  Defaults to the legacy SOAP path (:class:`BfabricUser`).
        """
        self.app: ASGI3Application = app
        self.token_validator: TokenValidatorStrategy = token_validator
        self.landing_path: str = landing_path
        self.hooks: AuthHooks | None = hooks
        self.token_param: str = token_param
        self.authenticated_path: str = authenticated_path
        self.logout_path: str = logout_path
        self.renderer: ResponseRenderer = renderer or HTMLRenderer()
        self._session_factory: SessionFactory = session_factory or _default_session_factory
        self._user_factory: UserFactory = user_factory or _default_user_factory

    async def __call__(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        try:
            # Handle middleware-provided operations
            if scope["type"] == "http":
                app_path = _strip_root_path(scope)
                if app_path == self.logout_path:
                    return await self._handle_logout(scope, receive, send)
                if app_path == self.landing_path:
                    return await self._handle_landing(scope, receive, send)

            # Ensure authentication is provided
            if scope["type"] == "http" or scope["type"] == "websocket":
                # Get session data from scope (set by SessionMiddleware)
                session = scope.get("session", {})
                if "bfabric_session" in session:
                    # Pass the LIVE inner dict so user factories can write back to it
                    live_session_dict: MutableMapping[str, object] = session["bfabric_session"]  # type: ignore[assignment]  # pyright: ignore[reportAny]
                    scope["user"] = self._user_factory(live_session_dict)  # pyright: ignore[reportGeneralTypeIssues]
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

    async def _handle_reject(
        self, scope: HTTPScope | WebSocketScope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        """Handle rejection of authentication."""
        if self.hooks:
            handled = await self.hooks.on_reject(scope=scope)
            if handled:
                # If the hook handled the error, we do not display a custom message anymore.
                return None

        if scope["type"] == "websocket":
            return await self._send_websocket_close(send, 1008, "Not authenticated")
        else:
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
        if isinstance(result, TokenValidationError):
            return await self.renderer.render_error(ErrorResponse.invalid_token(), scope, receive, send)

        # Convert the validation result to a session dict via the factory
        new_session_dict = self._session_factory(result)

        # Store session data by modifying scope["session"] directly, this is supported by starlette's SessionMiddleware
        session = scope.get("session")
        if not is_valid_session_dict(session):
            return await self.renderer.render_error(ErrorResponse.invalid_session(), scope, receive, send)

        # If either user or B-Fabric instance is different, evict the session
        try:
            existing_bfabric_session = SessionData.model_validate(session.get("bfabric_session"))
        except ValidationError:
            existing_bfabric_session = None

        # Build a comparable session dict from the incoming result (for the legacy SOAP eviction check)
        try:
            new_session_data_for_eviction = SessionData.model_validate(new_session_dict)
        except ValidationError:
            new_session_data_for_eviction = None

        if (
            existing_bfabric_session is not None
            and new_session_data_for_eviction is not None
            and existing_bfabric_session != new_session_data_for_eviction
        ):
            session_cleared = False
            if self.hooks:
                session_cleared = await self.hooks.on_evict(session=session)

            if not session_cleared:
                logger.info("Clearing session due to user eviction")
                session.clear()

        # Invoke the landing callback, if configured, and determine the redirect URL
        redirect_url = self.authenticated_path
        if self.hooks is not None:
            token_data = result.token_data if isinstance(result, TokenValidationSuccess) else None  # type: ignore[union-attr]
            if token_data is not None:
                callback_result = await self.hooks.on_success(session=session, token_data=token_data)

                if callback_result is not None:
                    redirect_url = callback_result
                    logger.debug(f"Landing callback returned {callback_result}, redirecting.")
                else:
                    logger.debug("Landing callback returned None, redirecting to default authenticated_path.")

        # update the session
        session["bfabric_session"] = new_session_dict  # pyright: ignore[reportArgumentType]

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

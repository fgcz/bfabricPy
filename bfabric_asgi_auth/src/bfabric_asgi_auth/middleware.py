from __future__ import annotations

import urllib.parse

from asgiref.typing import ASGI3Application, ASGIReceiveCallable, ASGISendCallable, Scope
from loguru import logger
from pydantic import SecretStr, ValidationError

from bfabric_asgi_auth.response_renderer import (
    ErrorResponse,
    PlainTextRenderer,
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
    ) -> None:
        """Initialize the middleware.

        :param app: The ASGI application to wrap
        :param token_validator: Token validator instance
        :param landing_path: URL path for landing page (default: /landing)
        :param hooks: Authentication hooks for customizing behavior (default: None)
        :param token_param: Query parameter name for token (default: token)
        :param authenticated_path: Path to redirect to after successful authentication (default: /)
        :param logout_path: URL path for logout (default: /logout)
        :param renderer: Response renderer for customizing error/success pages (default: PlainTextRenderer)
        """
        self.app: ASGI3Application = app
        self.token_validator: TokenValidatorStrategy = token_validator
        self.landing_path: str = landing_path
        self.hooks: AuthHooks | None = hooks
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
            if "bfabric_session" in session:
                return await self.app(scope, receive, send)
            else:
                return await self._handle_reject(scope=scope, receive=receive, send=send)
        elif scope["type"] == "lifespan":
            return await self.app(scope, receive, send)
        else:
            # We reject unknown scopes, this might need to be extended in the future.
            logger.warning(f"Dropping unknown scope: {scope['type']}")  # pyright: ignore[reportUnreachable]
            return None

    async def _handle_reject(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
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
        if not isinstance(result, TokenValidationSuccess):
            return await self.renderer.render_error(ErrorResponse.invalid_token(), scope, receive, send)

        # Create session data
        session_data = SessionData(
            bfabric_instance=result.token_data.caller,
            bfabric_auth_login=result.token_data.user,
            bfabric_auth_password=result.token_data.user_ws_password.get_secret_value(),
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
            if self.hooks:
                try:
                    await self.hooks.on_evict(session=session)
                except VisibleException as e:
                    return await self.renderer.render_error(e.response, scope, receive, send)
                except Exception:
                    logger.exception("eviction callback failed")
                    return await self.renderer.render_error(ErrorResponse.callback_error("evict"), scope, receive, send)

        # Invoke the landing callback, if configured, and determine the redirect URL
        redirect_url = self.authenticated_path
        if self.hooks is not None:
            try:
                callback_result = await self.hooks.on_success(session=session, token_data=result.token_data)
            except VisibleException as e:
                return await self.renderer.render_error(e.response, scope, receive, send)
            except Exception:
                logger.exception("Landing callback failed")
                return await self.renderer.render_error(ErrorResponse.callback_error("landing"), scope, receive, send)

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

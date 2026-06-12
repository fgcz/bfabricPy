from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, TypeGuard

from asgiref.typing import HTTPScope, WebSocketScope
from bfabric.experimental.webapp_oauth import UrlTokenContext  # noqa: TC002

JsonRepresentable = str | int | float | bool | None | Mapping[str, "JsonRepresentable"] | Sequence["JsonRepresentable"]


class AuthHooks(Protocol):
    async def on_reject(self, scope: HTTPScope | WebSocketScope) -> bool:
        """Called when a request is rejected. If return value is False and scope type is HTTP, a default message will be displayed."""
        return False

    async def on_success(self, session: dict[str, JsonRepresentable], context: UrlTokenContext) -> str | None:
        """Called on successful authentication. If the return value is not None, it is used as the redirect URL."""
        return None

    async def on_logout(self, session: dict[str, JsonRepresentable]) -> str | None:
        """Called on logout. If the return value is not None, it is used as the redirect URL."""
        return None

    async def on_evict(self, session: dict[str, JsonRepresentable]) -> bool:
        """Reserved for deferred eviction support (user-switch detection).

        Not currently invoked — eviction is deferred to a follow-up change.
        When re-enabled, returning True suppresses the default ``session.clear()``.
        """
        return False


def is_json_representable(value: Any) -> TypeGuard[JsonRepresentable]:  # pyright: ignore[reportAny, reportExplicitAny]
    """Check if a value is JSON representable."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return True
    if isinstance(value, dict):
        return all(
            isinstance(k, str) and is_json_representable(v)
            for k, v in value.items()  # pyright: ignore[reportUnknownVariableType]
        )
    if isinstance(value, list):
        return all(is_json_representable(item) for item in value)  # pyright: ignore[reportUnknownVariableType]
    return False


def is_valid_session_dict(
    session: Any,  # pyright: ignore[reportAny, reportExplicitAny]
) -> TypeGuard[dict[str, JsonRepresentable]]:
    """Check if session is a valid dict with string keys and JSON representable values."""
    if not isinstance(session, dict):
        return False
    return all(
        isinstance(key, str) and is_json_representable(value)
        for key, value in session.items()  # pyright: ignore[reportUnknownVariableType]
    )

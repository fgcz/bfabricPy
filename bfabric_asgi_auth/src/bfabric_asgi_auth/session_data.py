from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, model_validator


class SessionState(str, Enum):
    """Session lifecycle states."""

    NEW = "new"  # Token validated, session created, not yet initialized
    READY = "ready"  # Session initialized and ready for use
    ERROR = "error"  # Session encountered an error during initialization


class SessionData(BaseModel):
    """Session data stored for authenticated users."""

    state: SessionState
    token: str  # The authentication token
    client_config: dict[str, Any] | None = None  # Bfabric client configuration
    user_info: dict[str, Any] | None = None  # User information from token validation
    error: str | None = None  # Error message if state is ERROR

    @model_validator(mode="after")
    def state_constraints(self) -> SessionData:
        """Validate state transitions and requirements."""
        if self.state == SessionState.NEW:
            if self.error:
                msg = "Session in NEW state must not have an error"
                raise ValueError(msg)
        elif self.state == SessionState.READY:
            if self.error:
                msg = "Session in READY state must not have an error"
                raise ValueError(msg)
            if not self.client_config:
                msg = "Session in READY state must have client_config"
                raise ValueError(msg)
        elif self.state == SessionState.ERROR:
            if not self.error:
                msg = "Session in ERROR state must have an error message"
                raise ValueError(msg)
        return self

    def update_ready(self, client_config: dict[str, Any], user_info: dict[str, Any] | None = None) -> SessionData:
        """Update session to READY state.

        Args:
            client_config: Bfabric client configuration
            user_info: Optional user information

        Returns:
            Updated session data

        Raises:
            ValueError: If session is not in NEW state
        """
        if self.state != SessionState.NEW:
            msg = "Session must be in NEW state to update to READY"
            raise ValueError(msg)
        return SessionData(
            state=SessionState.READY,
            token=self.token,
            client_config=client_config,
            user_info=user_info,
            error=None,
        )

    def update_error(self, error: str) -> SessionData:
        """Update session to ERROR state.

        Args:
            error: Error message

        Returns:
            Updated session data

        Raises:
            ValueError: If session is not in NEW state
        """
        if self.state != SessionState.NEW:
            msg = "Session must be in NEW state to update to ERROR"
            raise ValueError(msg)
        return SessionData(
            state=SessionState.ERROR,
            token=self.token,
            client_config=None,
            user_info=None,
            error=error,
        )

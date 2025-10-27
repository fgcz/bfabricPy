from __future__ import annotations

import time
import uuid
from typing import Any


class SessionStoreMem:
    """In-memory session store with TTL support."""

    def __init__(self, default_ttl: int = 3600):
        """Initialize session store.

        :param default_ttl: Default time-to-live for sessions in seconds (default: 1 hour)
        :type default_ttl: int
        """
        self._sessions: dict[str, dict[str, Any]] = {}
        self._default_ttl = default_ttl

    def create(self, session_data: dict[str, Any], ttl: int | None = None) -> str:
        """Create a new session and return its ID.

        :param session_data: Data to store in the session
        :param ttl: Time-to-live in seconds (uses default if not specified)
        :returns: The generated session ID
        :rtype: str
        """
        session_id = str(uuid.uuid4())
        expiry = time.time() + (ttl or self._default_ttl)

        self._sessions[session_id] = {
            "data": session_data,
            "expiry": expiry,
        }

        return session_id

    def get(self, session_id: str) -> dict[str, Any] | None:
        """Get session data by ID.

        :param session_id: The session ID to retrieve
        :returns: Session data if found and not expired, None otherwise
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if time.time() > session["expiry"]:
            self.delete(session_id)
            return None

        return session["data"]

    def update(self, session_id: str, session_data: dict[str, Any]) -> bool:
        """Update session data, by replacing the existing data.

        :param session_id: The session ID to update
        :param session_data: New session data
        :returns: True if updated, False if session not found or expired
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False

        # Check if expired
        if time.time() > session["expiry"]:
            self.delete(session_id)
            return False

        session["data"] = session_data
        return True

    def delete(self, session_id: str) -> bool:
        """Delete a session.

        :param session_id: The session ID to delete
        :returns: True if deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove all expired sessions.

        :returns: Number of sessions removed
        """
        now = time.time()
        expired = [session_id for session_id, session in self._sessions.items() if now > session["expiry"]]

        for session_id in expired:
            del self._sessions[session_id]

        return len(expired)

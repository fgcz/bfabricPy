"""Tests for OAuthSessionData."""

from __future__ import annotations

import json
import datetime

import pytest

from bfabric._oauth.url_token import UrlTokenContext
from bfabric_asgi_auth.oauth_session_data import OAuthSessionData


@pytest.fixture
def sample_context() -> UrlTokenContext:
    return UrlTokenContext(
        entity_id=7,
        entity_class_name="Workunit",
        application_id=3,
        job_id=99,
        subject="alice",
        expires_at=datetime.datetime(2099, 1, 1, tzinfo=datetime.timezone.utc),
    )


@pytest.fixture
def sample_token() -> dict[str, object]:
    return {"access_token": "at123", "refresh_token": "rt456", "token_type": "Bearer"}


class TestOAuthSessionData:
    def test_has_minimal_fields(self, sample_token, sample_context):
        """OAuthSessionData stores only base_url, token, context — no client_id."""
        data = OAuthSessionData(
            base_url="https://example.com/bfabric",
            token=sample_token,
            context=sample_context,
        )
        # No client_id field
        assert not hasattr(data, "client_id")
        assert data.base_url == "https://example.com/bfabric"
        assert data.token == sample_token
        assert data.context.subject == "alice"

    def test_json_serializable(self, sample_token, sample_context):
        """model_dump(mode='json') must be json.dumps-compatible (datetime → ISO string)."""
        data = OAuthSessionData(
            base_url="https://example.com/bfabric",
            token=sample_token,
            context=sample_context,
        )
        dumped = data.model_dump(mode="json")
        # Should not raise
        serialized = json.dumps(dumped)
        assert "alice" in serialized
        # datetime should be an ISO string, not a datetime object (field name is "expires_at")
        assert isinstance(dumped["context"]["expires_at"], str)

    def test_round_trips(self, sample_token, sample_context):
        """model_dump / model_validate round-trip preserves all fields."""
        original = OAuthSessionData(
            base_url="https://example.com/bfabric",
            token=sample_token,
            context=sample_context,
        )
        dumped = original.model_dump(mode="json")
        restored = OAuthSessionData.model_validate(dumped)
        assert restored.base_url == original.base_url
        assert restored.token == original.token
        assert restored.context.subject == original.context.subject
        assert restored.context.entity_id == original.context.entity_id
        assert restored.context.expires_at == original.context.expires_at

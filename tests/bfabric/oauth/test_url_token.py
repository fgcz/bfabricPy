from __future__ import annotations

import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from bfabric._oauth.url_token import UrlTokenContext, _jwks_cache, parse_url_token, verify_jwt


@pytest.fixture(autouse=True)
def clear_jwks_cache():
    _jwks_cache.clear()
    yield
    _jwks_cache.clear()


SAMPLE_CLAIMS = {
    "entityId": 123,
    "entityClassName": "Workunit",
    "applicationId": 456,
    "jobId": 789,
    "client_id": "my-client",
    "sub": "jdoe",
    "exp": 1999999999,
}


@pytest.fixture
def mock_httpx_get():
    with patch("bfabric._oauth.url_token.httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"keys": [{"kty": "RSA", "kid": "1"}]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_joserfc():
    with (
        patch("bfabric._oauth.url_token.KeySet") as mock_key_set,
        patch("bfabric._oauth.url_token.joserfc_jwt") as mock_jwt,
    ):
        mock_result = MagicMock()
        mock_result.claims = dict(SAMPLE_CLAIMS)
        mock_jwt.decode.return_value = mock_result
        mock_jwt.JWTClaimsRegistry.return_value = MagicMock()
        yield mock_key_set, mock_jwt, mock_result


class TestVerifyJwt:
    def test_fetches_jwks_and_verifies(self, mock_httpx_get, mock_joserfc):
        mock_key_set, mock_jwt, mock_result = mock_joserfc

        result = verify_jwt("https://example.com/bfabric", "some.jwt.token")

        mock_httpx_get.assert_called_once_with("https://example.com/bfabric/rest/oauth/jwks")
        mock_key_set.import_key_set.assert_called_once()
        mock_jwt.decode.assert_called_once_with("some.jwt.token", mock_key_set.import_key_set.return_value)
        assert result == dict(SAMPLE_CLAIMS)

    def test_caches_jwks(self, mock_httpx_get, mock_joserfc):
        verify_jwt("https://example.com/bfabric", "token1")
        verify_jwt("https://example.com/bfabric", "token2")
        assert mock_httpx_get.call_count == 1

    def test_refetches_expired_jwks(self, mock_httpx_get, mock_joserfc):
        verify_jwt("https://example.com/bfabric", "token1")
        # Manually expire the cache
        base_url = "https://example.com/bfabric"
        jwks, _ = _jwks_cache[base_url]
        _jwks_cache[base_url] = (jwks, time.time() - 7200)

        verify_jwt("https://example.com/bfabric", "token2")
        assert mock_httpx_get.call_count == 2

    def test_normalizes_trailing_slash(self, mock_httpx_get, mock_joserfc):
        verify_jwt("https://example.com/bfabric/", "token")
        mock_httpx_get.assert_called_once_with("https://example.com/bfabric/rest/oauth/jwks")


class TestParseUrlToken:
    def test_extracts_all_claims(self, mock_httpx_get, mock_joserfc):
        ctx = parse_url_token("https://example.com/bfabric", "some.jwt.token")

        assert ctx.entity_id == 123
        assert ctx.entity_class_name == "Workunit"
        assert ctx.application_id == 456
        assert ctx.job_id == 789
        assert ctx.client_id == "my-client"
        assert ctx.subject == "jdoe"
        assert ctx.expires_at == datetime.fromtimestamp(1999999999, tz=UTC)

    def test_handles_missing_optional_claims(self, mock_httpx_get):
        minimal_claims = {"sub": "user", "exp": 1999999999}
        with (
            patch("bfabric._oauth.url_token.KeySet"),
            patch("bfabric._oauth.url_token.joserfc_jwt") as mock_jwt,
        ):
            mock_result = MagicMock()
            mock_result.claims = dict(minimal_claims)
            mock_jwt.decode.return_value = mock_result
            mock_jwt.JWTClaimsRegistry.return_value = MagicMock()

            ctx = parse_url_token("https://example.com/bfabric", "token")

        assert ctx.entity_id is None
        assert ctx.entity_class_name is None
        assert ctx.application_id is None
        assert ctx.job_id is None
        assert ctx.client_id is None
        assert ctx.subject == "user"
        assert ctx.expires_at is not None

    def test_returns_frozen_dataclass(self, mock_httpx_get, mock_joserfc):
        ctx = parse_url_token("https://example.com/bfabric", "token")
        assert isinstance(ctx, UrlTokenContext)
        with pytest.raises(AttributeError):
            ctx.entity_id = 999  # type: ignore[misc]

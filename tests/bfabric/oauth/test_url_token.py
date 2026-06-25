from __future__ import annotations

import time

import pytest
from joserfc.errors import JoseError

from bfabric._oauth.url_token import _jwks_cache, verify_jwt


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
def mock_httpx_get(mocker):
    mock_get = mocker.patch("bfabric._oauth.url_token.httpx.get")
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {"keys": [{"kty": "RSA", "kid": "1"}]}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    return mock_get


@pytest.fixture
def mock_joserfc(mocker):
    mock_key_set = mocker.patch("bfabric._oauth.url_token.KeySet")
    mock_jwt = mocker.patch("bfabric._oauth.url_token.joserfc_jwt")
    mock_result = mocker.MagicMock()
    mock_result.claims = dict(SAMPLE_CLAIMS)
    mock_jwt.decode.return_value = mock_result
    mock_jwt.JWTClaimsRegistry.return_value = mocker.MagicMock()
    return mock_key_set, mock_jwt, mock_result


class TestVerifyJwt:
    def test_fetches_jwks_and_verifies(self, mock_httpx_get, mock_joserfc):
        mock_key_set, mock_jwt, mock_result = mock_joserfc

        result = verify_jwt("https://example.com/bfabric", "some.jwt.token")

        mock_httpx_get.assert_called_once_with("https://example.com/bfabric/rest/oauth/jwks", timeout=30)
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
        mock_httpx_get.assert_called_once_with("https://example.com/bfabric/rest/oauth/jwks", timeout=30)


class TestVerifyJwtClaims:
    """Tests for opt-in aud/iss validation.

    These deliberately do NOT use the ``mock_joserfc`` fixture: it stubs out
    ``JWTClaimsRegistry`` wholesale, but the aud/iss behavior lives *inside*
    ``JWTClaimsRegistry.validate``. We mock only the JWKS fetch + ``decode`` and leave the real
    registry so ``validate`` genuinely runs the check.
    """

    EXP = 1999999999  # far-future expiry so the real registry does not reject on expiry

    @staticmethod
    def _decode_returns(mocker, claims):
        mocker.patch("bfabric._oauth.url_token._fetch_jwks", return_value={"keys": []})
        mocker.patch("bfabric._oauth.url_token.KeySet")
        result = mocker.MagicMock()
        result.claims = claims
        mocker.patch("bfabric._oauth.url_token.joserfc_jwt.decode", return_value=result)

    def test_no_validation_by_default(self, mocker):
        self._decode_returns(mocker, {"sub": "jdoe", "aud": "anything", "exp": self.EXP})
        result = verify_jwt("https://example.com/bfabric", "tok")
        assert result["sub"] == "jdoe"

    def test_matching_audience_and_issuer(self, mocker):
        self._decode_returns(mocker, {"aud": "client-x", "iss": "https://iss", "exp": self.EXP})
        result = verify_jwt("https://example.com/bfabric", "tok", audience="client-x", issuer="https://iss")
        assert result["aud"] == "client-x"

    def test_mismatched_audience_raises(self, mocker):
        self._decode_returns(mocker, {"aud": "other", "exp": self.EXP})
        with pytest.raises(JoseError):
            verify_jwt("https://example.com/bfabric", "tok", audience="client-x")

    def test_missing_required_audience_raises(self, mocker):
        self._decode_returns(mocker, {"sub": "jdoe", "exp": self.EXP})
        with pytest.raises(JoseError):
            verify_jwt("https://example.com/bfabric", "tok", audience="client-x")

    def test_mismatched_issuer_raises(self, mocker):
        self._decode_returns(mocker, {"iss": "https://evil", "exp": self.EXP})
        with pytest.raises(JoseError):
            verify_jwt("https://example.com/bfabric", "tok", issuer="https://iss")

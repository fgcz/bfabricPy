from __future__ import annotations

import time

import pytest

from bfabric.config import BaseUrl
from bfabric.oauth._url_token import UrlTokenContext, _jwks_cache, verify_jwt


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
    mock_get = mocker.patch("bfabric.oauth._url_token.httpx.get")
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {"keys": [{"kty": "RSA", "kid": "1"}]}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    return mock_get


@pytest.fixture
def mock_joserfc(mocker):
    mock_key_set = mocker.patch("bfabric.oauth._url_token.KeySet")
    mock_jwt = mocker.patch("bfabric.oauth._url_token.joserfc_jwt")
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
        # The slash is dropped by BaseUrl at the boundary, so no doubled slash reaches the JWKS URL.
        verify_jwt(BaseUrl("https://example.com/bfabric/"), "token")
        mock_httpx_get.assert_called_once_with("https://example.com/bfabric/rest/oauth/jwks", timeout=30)


class TestBaseUrlFromIssuer:
    @pytest.mark.parametrize("issuer", ["https://example.com/bfabric", "https://example.com/bfabric/"])
    def test_canonicalises_the_issuer(self, issuer):
        assert UrlTokenContext(iss=issuer).base_url == "https://example.com/bfabric"

    def test_is_none_without_an_issuer(self):
        assert UrlTokenContext().base_url is None

    def test_rejects_a_non_http_issuer(self):
        # A verified token naming itself with something we cannot call back is a server-side defect.
        with pytest.raises(ValueError, match="Not a valid http"):
            _ = UrlTokenContext(iss="urn:example:issuer").base_url

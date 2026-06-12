from __future__ import annotations

import time

import pytest

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

    def test_audience_forwarded_to_claims_registry(self, mock_httpx_get, mock_joserfc):
        """When audience is provided, it is added to the claims validation."""
        _, mock_jwt, _ = mock_joserfc
        verify_jwt("https://example.com/bfabric", "token", audience="my-client")
        call_kwargs = mock_jwt.JWTClaimsRegistry.call_args[1]
        assert "aud" in call_kwargs
        assert call_kwargs["aud"] == {"essential": True, "value": "my-client"}

    def test_issuer_forwarded_to_claims_registry(self, mock_httpx_get, mock_joserfc):
        """When issuer is provided, it is added to the claims validation."""
        _, mock_jwt, _ = mock_joserfc
        verify_jwt("https://example.com/bfabric", "token", issuer="https://example.com")
        call_kwargs = mock_jwt.JWTClaimsRegistry.call_args[1]
        assert "iss" in call_kwargs
        assert call_kwargs["iss"] == {"essential": True, "value": "https://example.com"}

    def test_default_omits_aud_and_iss(self, mock_httpx_get, mock_joserfc):
        """Default call (no audience/issuer) does not add aud or iss to the registry."""
        _, mock_jwt, _ = mock_joserfc
        verify_jwt("https://example.com/bfabric", "token")
        call_kwargs = mock_jwt.JWTClaimsRegistry.call_args[1]
        assert "aud" not in call_kwargs
        assert "iss" not in call_kwargs

    def test_real_key_wrong_audience_rejected(self, mocker):
        """Real RSA key round-trip: wrong audience raises when opt-in is active."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        from joserfc import jwt as joserfc_jwt
        from joserfc.jwk import OctKey, RSAKey

        # Generate a real RSA key pair
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        jwk_private = RSAKey.import_key(private_key)
        jwk_public = RSAKey.import_key(private_key.public_key())

        # Sign a token with audience "correct-client"
        token = joserfc_jwt.encode(
            {"alg": "RS256"},
            {"sub": "user", "aud": "correct-client", "exp": 9999999999},
            jwk_private,
        )
        # Mock JWKS endpoint to return the public key
        jwks_data = {"keys": [jwk_public.as_dict(private=False)]}
        mocker.patch("bfabric._oauth.url_token.httpx.get").return_value.__class__  # type: ignore[misc]
        mock_resp = mocker.MagicMock()
        mock_resp.json.return_value = jwks_data
        mock_resp.raise_for_status.return_value = None
        mocker.patch("bfabric._oauth.url_token.httpx.get", return_value=mock_resp)

        # Wrong audience should fail
        from joserfc.errors import InvalidClaimError

        with pytest.raises(InvalidClaimError):
            verify_jwt("https://example.com/bfabric", token, audience="wrong-client")

    def test_real_key_default_accepts_any_audience(self, mocker):
        """Default path (no audience param) accepts a token with any aud value."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        from joserfc import jwt as joserfc_jwt
        from joserfc.jwk import RSAKey

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        jwk_private = RSAKey.import_key(private_key)
        jwk_public = RSAKey.import_key(private_key.public_key())

        token = joserfc_jwt.encode(
            {"alg": "RS256"},
            {"sub": "user", "aud": "some-arbitrary-client", "exp": 9999999999},
            jwk_private,
        )
        jwks_data = {"keys": [jwk_public.as_dict(private=False)]}
        mock_resp = mocker.MagicMock()
        mock_resp.json.return_value = jwks_data
        mock_resp.raise_for_status.return_value = None
        mocker.patch("bfabric._oauth.url_token.httpx.get", return_value=mock_resp)

        # Should not raise — aud is not validated by default
        claims = verify_jwt("https://example.com/bfabric", token)
        assert claims["aud"] == "some-arbitrary-client"

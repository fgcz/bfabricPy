from __future__ import annotations

import pytest

from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric.transfer.errors import ScopeError
from bfabric.transfer.tokens import (
    _decode_scopes,
    check_download_scope,
    check_upload_scope,
    require_scope,
    token_provider,
)


def _oauth_client(mocker, token: str):
    client = mocker.MagicMock()
    client.auth = mocker.MagicMock(login=OAUTH_LOGIN, password=mocker.MagicMock())
    client.auth.password.get_secret_value.return_value = token
    return client


def _login_client(mocker, login: str = "someuser"):
    client = mocker.MagicMock()
    client.auth = mocker.MagicMock(login=login, password=mocker.MagicMock())
    return client


def _no_auth_client(mocker):
    client = mocker.MagicMock()
    type(client).auth = mocker.PropertyMock(side_effect=ValueError("Authentication not available"))
    return client


class TestTokenProvider:
    def test_oauth_client_returns_token_callable(self, mocker):
        client = _oauth_client(mocker, "the-token")

        provider = token_provider(client)

        assert callable(provider)
        assert provider() == "the-token"

    def test_non_oauth_client_returns_none(self, mocker):
        client = _login_client(mocker, "someuser")

        assert token_provider(client) is None

    def test_no_auth_client_returns_none(self, mocker):
        client = _no_auth_client(mocker)

        assert token_provider(client) is None


class TestRequireScope:
    def test_granted_scope_does_not_raise(self, mocker, make_jwt):
        client = _oauth_client(mocker, make_jwt({"scope": "api:read tus containers"}))

        require_scope(client, "tus")

    def test_missing_scope_raises_with_hint(self, mocker, make_jwt):
        client = _oauth_client(mocker, make_jwt({"scope": "api:read"}))

        with pytest.raises(ScopeError) as exc_info:
            require_scope(client, "tus")

        message = str(exc_info.value)
        assert "tus" in message
        assert "bfabric-cli auth login --scope" in message

    def test_non_oauth_client_skips(self, mocker):
        client = _login_client(mocker, "someuser")

        require_scope(client, "tus")

    def test_undecodable_token_skips(self, mocker):
        client = _oauth_client(mocker, "not-a-jwt")

        require_scope(client, "tus")

    def test_no_auth_client_skips(self, mocker):
        client = _no_auth_client(mocker)

        require_scope(client, "tus")


class TestDecodeScopes:
    def test_scope_as_space_delimited_string(self, make_jwt):
        token = make_jwt({"scope": "api:read api:write tus"})
        assert _decode_scopes(token) == {"api:read", "api:write", "tus"}

    def test_scope_as_list(self, make_jwt):
        token = make_jwt({"scope": ["api:read", "api:write", "tus"]})
        assert _decode_scopes(token) == {"api:read", "api:write", "tus"}

    def test_no_scope_claim(self, make_jwt):
        token = make_jwt({"sub": "jdoe"})
        assert _decode_scopes(token) == set()

    def test_extra_whitespace_in_string_form(self, make_jwt):
        token = make_jwt({"scope": "  api:read   api:write \t tus  "})
        assert _decode_scopes(token) == {"api:read", "api:write", "tus"}

    @pytest.mark.parametrize(
        "bad_token",
        [
            "not-a-jwt",
            "only.two",
            "one.two.three.four",
            "not-base64!!.not-base64!!.sig",
        ],
    )
    def test_malformed_token_raises(self, bad_token):
        with pytest.raises(ValueError):
            _decode_scopes(bad_token)

    def test_payload_not_a_json_object_string(self, make_jwt):
        token = make_jwt("just-a-string")
        with pytest.raises(ValueError):
            _decode_scopes(token)

    def test_payload_not_a_json_object_number(self, make_jwt):
        token = make_jwt(42)
        with pytest.raises(ValueError):
            _decode_scopes(token)

    def test_payload_requiring_padding_decodes_fine(self, make_jwt):
        # Chosen so the base64url payload segment length is not a multiple of 4,
        # exercising the padding logic in _decode_scopes.
        payload = {"scope": "a"}
        token = make_jwt(payload)
        segments = token.split(".")
        assert len(segments[1]) % 4 != 0
        assert _decode_scopes(token) == {"a"}


class TestCheckScopeHelpers:
    def test_check_upload_scope_grants_tus(self, mocker, make_jwt):
        client = _oauth_client(mocker, make_jwt({"scope": "api:read tus"}))

        check_upload_scope(client)

    def test_check_upload_scope_missing_tus_raises(self, mocker, make_jwt):
        client = _oauth_client(mocker, make_jwt({"scope": "api:read containers"}))

        with pytest.raises(ScopeError) as exc_info:
            check_upload_scope(client)
        assert "tus" in str(exc_info.value)

    def test_check_download_scope_grants_containers(self, mocker, make_jwt):
        client = _oauth_client(mocker, make_jwt({"scope": "api:read containers"}))

        check_download_scope(client)

    def test_check_download_scope_missing_containers_raises(self, mocker, make_jwt):
        client = _oauth_client(mocker, make_jwt({"scope": "api:read tus"}))

        with pytest.raises(ScopeError) as exc_info:
            check_download_scope(client)
        assert "containers" in str(exc_info.value)

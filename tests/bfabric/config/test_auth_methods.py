from __future__ import annotations

import pytest
from pydantic import SecretStr

from bfabric.config.auth_methods import (
    AUTH_METHOD_CLASSES,
    ClientCredentialsAuth,
    ClientRegistration,
    InteractiveOAuthAuth,
    NoAuth,
    PasswordAuth,
    PatAuth,
    UnknownAuth,
    auth_method_from_flat,
    auth_owned_keys,
    registration_from_flat,
)

OAUTH_ENV = {"auth_method": "oauth", "client_id": "CLI", "scope": "api:read"}
PAT_ENV = {"auth_method": "pat", "pat": "short-token"}
SVCACCT_ENV = {
    "auth_method": "client_credentials",
    "client_id": "svc",
    "client_secret": "s3cret",
    "scope": "api:read",
}
PASSWORD_ENV = {"auth_method": "password", "login": "user", "password": "p" * 32}
LEGACY_ENV = {"login": "user", "password": "p" * 32}


class TestAuthOwnedKeys:
    def test_matches_frozen_yaml_contract(self):
        assert auth_owned_keys() == frozenset(
            {
                "auth_method",
                "login",
                "password",
                "pat",
                "client_id",
                "client_secret",
                "scope",
                "registration_access_token",
                "registration_client_uri",
            }
        )

    def test_excludes_non_yaml_fields(self):
        assert "auth_method_written" not in auth_owned_keys()
        assert "kind" not in auth_owned_keys()
        assert "extra" not in auth_owned_keys()

    def test_every_variant_is_registered(self):
        kinds = {cls.model_fields["kind"].default for cls in AUTH_METHOD_CLASSES}
        assert kinds == {"password", "pat", "oauth", "client_credentials", "none", "unknown"}


class TestParsing:
    @pytest.mark.parametrize(
        ("flat", "expected"),
        [
            (OAUTH_ENV, InteractiveOAuthAuth),
            (PAT_ENV, PatAuth),
            (SVCACCT_ENV, ClientCredentialsAuth),
            (PASSWORD_ENV, PasswordAuth),
            (LEGACY_ENV, PasswordAuth),
            ({}, NoAuth),
            ({"auth_method": "device_code"}, UnknownAuth),
        ],
    )
    def test_variant(self, flat, expected):
        assert isinstance(auth_method_from_flat(flat), expected)

    def test_declared_oauth_wins_over_a_stale_login(self):
        """connect() routes on auth_method, so a leftover login must not shadow it."""
        parsed = auth_method_from_flat({"auth_method": "oauth", "login": "user", "password": "p" * 32})
        assert isinstance(parsed, InteractiveOAuthAuth)

    def test_undeclared_login_is_a_password_env(self):
        assert isinstance(auth_method_from_flat(LEGACY_ENV), PasswordAuth)

    def test_undeclared_oauth_keys_are_preserved(self):
        """The CLI records client_id/scope for a replayable re-login without declaring a method."""
        parsed = auth_method_from_flat({"scope": "api:write"})
        assert isinstance(parsed, InteractiveOAuthAuth)
        assert parsed.scope == "api:write"
        assert parsed.to_flat() == {"scope": "api:write"}

    def test_undeclared_client_id_is_preserved(self):
        parsed = auth_method_from_flat({"client_id": "CLI"})
        assert parsed.to_flat() == {"client_id": "CLI"}

    def test_undeclared_pat_is_honoured(self):
        assert isinstance(auth_method_from_flat({"pat": "token"}), PatAuth)

    def test_rc1_legacy_oauth_shape(self):
        """1.20.0rc1 wrote login: __oauth__ with a short inline password."""
        parsed = auth_method_from_flat({"login": "__oauth__", "password": "short"})
        assert isinstance(parsed, PasswordAuth)
        assert parsed.static_auth().password.get_secret_value() == "short"

    def test_oauth_without_client_id_still_parses(self):
        parsed = auth_method_from_flat({"auth_method": "oauth"})
        assert isinstance(parsed, InteractiveOAuthAuth)
        assert parsed.client_id is None

    def test_client_credentials_without_secret_still_parses(self):
        parsed = auth_method_from_flat({"auth_method": "client_credentials", "client_id": "svc"})
        assert isinstance(parsed, ClientCredentialsAuth)
        assert parsed.client_secret is None

    def test_pat_declared_but_missing_falls_back(self):
        assert isinstance(auth_method_from_flat({"auth_method": "pat"}), NoAuth)

    def test_password_declared_but_missing_login_falls_back(self):
        assert isinstance(auth_method_from_flat({"auth_method": "password"}), NoAuth)


class TestRoundTrip:
    @pytest.mark.parametrize(
        "flat",
        [OAUTH_ENV, PAT_ENV, SVCACCT_ENV, PASSWORD_ENV, LEGACY_ENV],
        ids=["oauth", "pat", "svcacct", "password", "legacy"],
    )
    def test_flat_to_flat_is_identity(self, flat):
        assert auth_method_from_flat(flat).to_flat() == flat

    def test_legacy_env_does_not_gain_auth_method(self):
        assert "auth_method" not in auth_method_from_flat(LEGACY_ENV).to_flat()

    def test_declared_password_keeps_auth_method(self):
        assert auth_method_from_flat(PASSWORD_ENV).to_flat()["auth_method"] == "password"

    def test_no_auth_emits_nothing(self):
        assert NoAuth().to_flat() == {}

    def test_unknown_method_preserves_sibling_keys(self):
        """Dropping them would delete data belonging to a method this version cannot parse."""
        flat = {"auth_method": "device_code", "client_id": "CLI", "scope": "api:read"}
        assert auth_method_from_flat(flat).to_flat() == flat


class TestStaticAuth:
    def test_password(self):
        auth = auth_method_from_flat(PASSWORD_ENV).static_auth()
        assert auth.login == "user"
        assert auth.password.get_secret_value() == "p" * 32

    def test_pat_uses_oauth_login(self):
        auth = auth_method_from_flat(PAT_ENV).static_auth()
        assert auth.login == "__oauth__"
        assert auth.password.get_secret_value() == "short-token"

    @pytest.mark.parametrize("flat", [OAUTH_ENV, SVCACCT_ENV, {}], ids=["oauth", "svcacct", "none"])
    def test_none_without_network(self, flat):
        assert auth_method_from_flat(flat).static_auth() is None


class TestCredentialProvider:
    @pytest.mark.parametrize("flat", [PASSWORD_ENV, PAT_ENV, {}], ids=["password", "pat", "none"])
    def test_static_methods_need_no_provider(self, flat):
        assert auth_method_from_flat(flat).credential_provider(base_url="https://x.test", env_name="PROD") is None

    def test_unknown_method_raises_only_when_used(self):
        parsed = auth_method_from_flat({"auth_method": "device_code"})
        with pytest.raises(ValueError, match="device_code"):
            parsed.credential_provider(base_url="https://x.test", env_name="PROD")

    def test_oauth_without_client_id_raises(self):
        parsed = auth_method_from_flat({"auth_method": "oauth"})
        with pytest.raises(ValueError, match="client_id"):
            parsed.credential_provider(base_url="https://x.test", env_name="PROD")

    def test_client_credentials_without_secret_raises(self):
        parsed = auth_method_from_flat({"auth_method": "client_credentials", "client_id": "svc"})
        with pytest.raises(ValueError, match="client_secret"):
            parsed.credential_provider(base_url="https://x.test", env_name="PROD")


class TestRegistration:
    def test_parses_a_complete_pair(self):
        registration = registration_from_flat(
            {"registration_access_token": "tok", "registration_client_uri": "https://x.test/reg"}
        )
        assert registration.registration_access_token.get_secret_value() == "tok"
        assert registration.registration_client_uri == "https://x.test/reg"

    @pytest.mark.parametrize(
        "flat",
        [{}, {"registration_access_token": "tok"}, {"registration_client_uri": "https://x.test/reg"}],
        ids=["absent", "token-only", "uri-only"],
    )
    def test_half_a_pair_is_tolerated_as_none(self, flat):
        assert registration_from_flat(flat) is None

    def test_round_trip(self):
        flat = {"registration_access_token": "tok", "registration_client_uri": "https://x.test/reg"}
        assert registration_from_flat(flat).to_flat() == flat

    def test_secret_not_in_repr(self):
        registration = ClientRegistration(
            registration_access_token=SecretStr("s3cret-token"),
            registration_client_uri="https://x.test/reg",
        )
        assert "s3cret-token" not in repr(registration)

"""Guards the config contracts a refactor must not change.

These pin the *current* on-disk and cross-process shapes so the auth-method refactor can be
verified as behaviour-preserving. They pass unchanged against the pre-refactor code by design.
"""

from __future__ import annotations

import copy
import json

import pytest
import yaml
from pydantic import SecretStr

from bfabric.config import BfabricAuth, BfabricClientConfig
from bfabric.config.config_data import ConfigData, export_config_data
from bfabric.config.config_file import ConfigFile, EnvironmentConfig
from bfabric.config.config_writer import _AUTH_OWNED_KEYS, _INLINE_SECRET_KEYS, write_environment_to_config


class TestAuthOwnedKeys:
    def test_exact_key_set(self):
        assert _AUTH_OWNED_KEYS == frozenset({"login", "password", "pat", "auth_method", "client_id", "scope"})

    def test_inline_secrets_are_auth_owned(self):
        assert set(_INLINE_SECRET_KEYS) <= _AUTH_OWNED_KEYS

    def test_reader_excludes_auth_keys_from_client_config(self):
        config = ConfigFile.model_validate(
            {
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": "https://example.com/bfabric",
                    "auth_method": "oauth",
                    "client_id": "CLI",
                    "scope": "api:read",
                },
            }
        )
        dumped = config.environments["PROD"].config.model_dump()
        assert not _AUTH_OWNED_KEYS & set(dumped)


class TestAuthMethodPropertyMatchesLegacyReader:
    """``auth_method`` reports only what the file actually declared."""

    @pytest.mark.parametrize(
        ("flat", "expected"),
        [
            ({"base_url": "https://example.com/bfabric", "scope": "api:write"}, None),
            ({"base_url": "https://example.com/bfabric", "client_id": "CLI"}, None),
            ({"base_url": "https://example.com/bfabric", "login": "u", "password": "p" * 32}, None),
            ({"base_url": "https://example.com/bfabric", "auth_method": "oauth", "client_id": "CLI"}, "oauth"),
            ({"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "t"}, "pat"),
            (
                {
                    "base_url": "https://example.com/bfabric",
                    "auth_method": "password",
                    "login": "u",
                    "password": "p" * 32,
                },
                "password",
            ),
        ],
    )
    def test_reported_auth_method(self, flat, expected):
        assert (
            ConfigFile.model_validate({"GENERAL": {"default_config": "PROD"}, "PROD": flat})
            .environments["PROD"]
            .auth_method
            == expected
        )


class TestConfigDataFrozenShape:
    def test_field_order(self):
        assert list(ConfigData.model_fields) == ["client", "auth", "auth_method", "client_id", "env_name"]

    def test_auth_has_no_default(self):
        """bfabric_rest_proxy / bfabric_asgi_auth construct ConfigData(client=..., auth=...)."""
        with pytest.raises(ValueError):
            ConfigData(client=BfabricClientConfig(base_url="https://example.com/bfabric"))

    def test_export_covers_every_field(self):
        """The hand-written export dict must not silently omit a field."""
        config_data = ConfigData(
            client=BfabricClientConfig(base_url="https://example.com/bfabric"),
            auth=BfabricAuth(login="user", password=SecretStr("p" * 32)),
            auth_method="oauth",
            client_id="CLI",
            env_name="PROD",
        )
        assert set(json.loads(export_config_data(config_data))) == set(ConfigData.model_fields)

    def test_export_keeps_secrets_readable(self):
        """SecretStr must be unwrapped, not serialized as '**********'."""
        config_data = ConfigData(
            client=BfabricClientConfig(base_url="https://example.com/bfabric"),
            auth=BfabricAuth(login="user", password=SecretStr("p" * 32)),
        )
        exported = json.loads(export_config_data(config_data))
        assert exported["auth"]["password"] == "p" * 32

    def test_override_json_round_trip(self):
        config_data = ConfigData(
            client=BfabricClientConfig(base_url="https://example.com/bfabric"),
            auth=BfabricAuth(login="user", password=SecretStr("p" * 32)),
            auth_method="oauth",
            client_id="CLI",
            env_name="PROD",
        )
        assert ConfigData.model_validate_json(export_config_data(config_data)) == config_data


class TestWriteSiteYamlKeys:
    """Each auth command's payload must land on disk as exactly these keys."""

    @pytest.mark.parametrize(
        ("env_data", "expected"),
        [
            (
                {
                    "base_url": "https://example.com/bfabric",
                    "auth_method": "oauth",
                    "client_id": "CLI",
                    "scope": "api:read",
                },
                {"base_url", "auth_method", "client_id", "scope"},
            ),
            (
                {"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "short-token"},
                {"base_url", "auth_method", "pat"},
            ),
            (
                {"base_url": "https://example.com/bfabric", "login": "user", "password": "p" * 32},
                {"base_url", "login", "password"},
            ),
        ],
    )
    def test_written_keys(self, tmp_path, env_data, expected):
        config_file = tmp_path / "config.yml"
        write_environment_to_config(config_file, "PROD", env_data, set_default=True)
        assert set(yaml.safe_load(config_file.read_text())["PROD"]) == expected

    def test_legacy_env_keeps_no_auth_method_key(self, tmp_path):
        """A password env written without auth_method must not gain one."""
        config_file = tmp_path / "config.yml"
        write_environment_to_config(
            config_file,
            "PROD",
            {"base_url": "https://example.com/bfabric", "login": "user", "password": "p" * 32},
            set_default=True,
        )
        assert "auth_method" not in yaml.safe_load(config_file.read_text())["PROD"]

    def test_mode_is_600(self, tmp_path):
        config_file = tmp_path / "config.yml"
        write_environment_to_config(config_file, "PROD", {"base_url": "https://example.com/bfabric"}, set_default=True)
        assert config_file.stat().st_mode & 0o777 == 0o600


class TestReaderDoesNotMutateInput:
    """The writers pass the mapping they are about to persist through the reader to validate it."""

    def test_config_file_validate_leaves_input_untouched(self):
        raw = {
            "GENERAL": {"default_config": "PROD"},
            "PROD": {"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "token"},
        }
        before = copy.deepcopy(raw)
        _ = ConfigFile.model_validate(raw)
        assert raw == before

    def test_environment_config_validate_leaves_input_untouched(self):
        raw = {"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "token"}
        before = copy.deepcopy(raw)
        _ = EnvironmentConfig.model_validate(raw)
        assert raw == before

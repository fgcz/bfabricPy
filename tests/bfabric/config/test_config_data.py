import os
from pathlib import Path

import pytest
from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric.config.config_data import ConfigData, export_config_data, load_config_data

from bfabric import BfabricClientConfig, BfabricAuth


@pytest.fixture
def client_config():
    return BfabricClientConfig(base_url="https://example.com/bfabric")


@pytest.fixture
def auth_config():
    return BfabricAuth(login="test-dummy", password="y" * 32)


@pytest.fixture
def config_data(client_config, auth_config):
    return ConfigData(client=client_config, auth=auth_config)


@pytest.fixture
def config_data_value(config_data) -> str:
    return export_config_data(config_data)


@pytest.mark.parametrize("auth", [None, BfabricAuth(login="changed-dummy", password="x" * 32)])
def test_with_auth(client_config, config_data, auth):
    result = config_data.with_auth(auth)
    assert result.client == client_config
    assert result.auth == auth


class TestLoadConfigData:
    @pytest.fixture
    def example_config_path(self) -> Path:
        return Path(__file__).parent / "example_config.yml"

    def test_from_env(self, mocker, config_data, config_data_value):
        mocker.patch.dict(os.environ, {"BFABRICPY_CONFIG_OVERRIDE": config_data_value})
        loaded_config = load_config_data(
            config_file_path="~/bfabricpy.yml", config_file_env="default", include_auth=True
        )
        assert loaded_config == config_data

    @pytest.mark.parametrize("include_auth", [True, False])
    def test_from_file_when_default(self, mocker, example_config_path, include_auth):
        mock_env = mocker.patch.dict(os.environ)
        mock_env.pop("BFABRICPY_CONFIG_OVERRIDE", None)
        mock_env.pop("BFABRICPY_CONFIG_ENV", None)
        loaded_config = load_config_data(
            config_file_path=example_config_path, config_file_env="default", include_auth=include_auth
        )
        assert loaded_config.client.base_url == "https://prod-server.example.com/bfabric"
        if include_auth:
            assert loaded_config.auth.login == "testuser"
        else:
            assert loaded_config.auth is None

    @pytest.mark.parametrize("include_auth", [True, False])
    def test_from_file_when_default_and_env(self, mocker, example_config_path, include_auth):
        mock_env = mocker.patch.dict(os.environ)
        mock_env.pop("BFABRICPY_CONFIG_OVERRIDE", None)
        mock_env["BFABRICPY_CONFIG_ENV"] = "TEST"
        loaded_config = load_config_data(
            config_file_path=example_config_path, config_file_env="default", include_auth=include_auth
        )
        assert loaded_config.client.base_url == "https://test-server.example.com/bfabric"
        if include_auth:
            assert loaded_config.auth.login == "testuser"
        else:
            assert loaded_config.auth is None

    @pytest.mark.parametrize("include_auth", [True, False])
    def test_from_file_when_default_and_override(self, mocker, example_config_path, include_auth):
        mock_env = mocker.patch.dict(os.environ)
        mock_env.pop("BFABRICPY_CONFIG_OVERRIDE", None)
        mock_env["BFABRICPY_CONFIG_ENV"] = "PRODUCTION"
        loaded_config = load_config_data(
            config_file_path=example_config_path, config_file_env="TEST", include_auth=include_auth
        )
        assert loaded_config.client.base_url == "https://test-server.example.com/bfabric"
        if include_auth:
            assert loaded_config.auth.login == "testuser"
        else:
            assert loaded_config.auth is None

    def test_from_file_not_allowed(self, mocker, example_config_path):
        mock_env = mocker.patch.dict(os.environ)
        mock_env.pop("BFABRICPY_CONFIG_OVERRIDE", None)
        mock_env["BFABRICPY_CONFIG_ENV"] = "TEST"
        with pytest.raises(ValueError, match="No configuration was found and config_file_env is set to None."):
            load_config_data(config_file_path=example_config_path, config_file_env=None, include_auth=True)

    def test_from_file_and_file_does_not_exist(self, mocker):
        mock_env = mocker.patch.dict(os.environ)
        mock_env.pop("BFABRICPY_CONFIG_OVERRIDE", None)
        mock_env["BFABRICPY_CONFIG_ENV"] = "TEST"
        with pytest.raises(OSError, match="No explicit config provided, and no config file found at"):
            load_config_data(config_file_path="/dev/null", config_file_env="TEST", include_auth=True)


def test_export_roundtrip(config_data):
    exported = export_config_data(config_data)
    loaded_config = ConfigData.model_validate_json(exported)
    assert loaded_config == config_data


def test_export_roundtrip_preserves_oauth_fields(client_config):
    config_data = ConfigData(
        client=client_config,
        auth=None,
        auth_method="oauth",
        client_id="my-app",
        env_name="PRODUCTION",
    )
    exported = export_config_data(config_data)
    loaded_config = ConfigData.model_validate_json(exported)
    assert loaded_config == config_data


class TestConfigDataOAuthFields:
    def test_defaults_none(self, client_config, auth_config):
        cd = ConfigData(client=client_config, auth=auth_config)
        assert cd.auth_method is None
        assert cd.client_id is None

    def test_with_auth_preserves_oauth_fields(self, client_config, auth_config):
        cd = ConfigData(client=client_config, auth=auth_config, auth_method="oauth", client_id="my-app")
        new_cd = cd.with_auth(None)
        assert new_cd.auth is None
        assert new_cd.auth_method == "oauth"
        assert new_cd.client_id == "my-app"

    def test_oauth_config_data(self, client_config):
        cd = ConfigData(client=client_config, auth=None, auth_method="oauth", client_id="my-app")
        assert cd.auth_method == "oauth"
        assert cd.client_id == "my-app"


class TestCredentialProvider:
    """Only the two OAuth methods need a provider; the rest authenticate from ``auth``."""

    def _config_data(self, **kwargs):
        return ConfigData(client=BfabricClientConfig(base_url="https://example.com/bfabric"), **kwargs)

    def test_pat_needs_no_provider(self):
        """A PAT lives in ``auth``, so asking for a provider must not warn or misclassify it."""
        config_data = self._config_data(
            auth=BfabricAuth(login=OAUTH_LOGIN, password="short-pat"),
            auth_method="pat",
            env_name="PROD",
        )
        assert config_data.credential_provider() is None

    def test_password_needs_no_provider(self):
        config_data = self._config_data(auth=BfabricAuth(login="user", password="p" * 32), auth_method="password")
        assert config_data.credential_provider() is None

    def test_no_auth_method_needs_no_provider(self):
        assert self._config_data(auth=None).credential_provider() is None

    def test_client_credentials_reports_the_missing_secret(self):
        config_data = self._config_data(auth=None, auth_method="client_credentials", client_id="svc", env_name="PROD")
        with pytest.raises(ValueError, match="client_secret"):
            _ = config_data.credential_provider()

    def test_oauth_reports_a_missing_client_id(self):
        config_data = self._config_data(auth=None, auth_method="oauth", env_name="PROD")
        with pytest.raises(ValueError, match="client_id"):
            _ = config_data.credential_provider()

import os
from pathlib import Path

import pytest
from logot import logged, Logot

from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric.config.config_file import ConfigFile, GeneralConfig, EnvironmentConfig, read_config_file


@pytest.fixture(autouse=True)
def reset_config_vars(mocker):
    mocker.patch.dict(os.environ, {}, clear=True)


@pytest.fixture()
def data_with_auth():
    return {
        "GENERAL": {"default_config": "PRODUCTION"},
        "PRODUCTION": {
            "login": "test-dummy",
            "password": "00000000001111111111222222222233",
            "base_url": "https://example.com",
        },
    }


@pytest.fixture()
def data_no_auth():
    return {
        "GENERAL": {"default_config": "PRODUCTION"},
        "PRODUCTION": {
            "base_url": "https://example.com",
        },
    }


@pytest.fixture()
def data_multiple():
    return {
        "GENERAL": {"default_config": "PRODUCTION"},
        "PRODUCTION": {
            "base_url": "https://example.com",
        },
        "TEST": {
            "base_url": "https://test.example.com",
            "login": "test-dummy",
            "password": "00000000001111111111222222222233",
        },
    }


@pytest.fixture()
def config_with_auth(data_with_auth):
    return ConfigFile.model_validate(data_with_auth)


def test_general_config(data_with_auth):
    config = GeneralConfig.model_validate(data_with_auth["GENERAL"])
    assert config.default_config == "PRODUCTION"


def test_environment_config_when_auth(data_with_auth):
    config = EnvironmentConfig.model_validate(data_with_auth["PRODUCTION"])
    assert config.config.base_url == "https://example.com/"
    assert config.auth.login == "test-dummy"
    assert config.auth.password.get_secret_value() == "00000000001111111111222222222233"


def test_environment_config_when_no_auth(data_no_auth):
    config = EnvironmentConfig.model_validate(data_no_auth["PRODUCTION"])
    assert config.config.base_url == "https://example.com/"
    assert config.auth is None


def test_environment_config_when_pat():
    """A PAT env (``auth_method: pat`` + inline ``pat``) builds an OAuth-style auth."""
    config = EnvironmentConfig.model_validate(
        {
            "base_url": "https://example.com",
            "auth_method": "pat",
            "pat": "short-pat-token",
        }
    )
    assert config.config.base_url == "https://example.com/"
    assert config.auth_method == "pat"
    assert config.auth.login == OAUTH_LOGIN
    assert config.auth.password.get_secret_value() == "short-pat-token"


def test_environment_config_when_legacy_oauth_login():
    """The legacy 1.20.0rc1 PAT shape (``login: __oauth__`` + inline ``password``) still reads."""
    config = EnvironmentConfig.model_validate(
        {
            "base_url": "https://example.com",
            "login": OAUTH_LOGIN,
            "password": "short-pat-token",
        }
    )
    assert config.auth.login == OAUTH_LOGIN
    assert config.auth.password.get_secret_value() == "short-pat-token"


def test_config_file_when_auth(data_with_auth):
    config = ConfigFile.model_validate(data_with_auth)
    assert config.general.default_config == "PRODUCTION"
    assert len(config.environments) == 1
    assert config.environments["PRODUCTION"].config.base_url == "https://example.com/"
    assert config.environments["PRODUCTION"].auth.login == "test-dummy"
    assert config.environments["PRODUCTION"].auth.password.get_secret_value() == "00000000001111111111222222222233"


def test_config_file_when_no_auth(data_no_auth):
    config = ConfigFile.model_validate(data_no_auth)
    assert config.general.default_config == "PRODUCTION"
    assert len(config.environments) == 1
    assert config.environments["PRODUCTION"].config.base_url == "https://example.com/"
    assert config.environments["PRODUCTION"].auth is None


def test_config_file_when_multiple(data_multiple):
    config = ConfigFile.model_validate(data_multiple)
    assert config.general.default_config == "PRODUCTION"
    assert len(config.environments) == 2
    assert config.environments["PRODUCTION"].config.base_url == "https://example.com/"
    assert config.environments["PRODUCTION"].auth is None
    assert config.environments["TEST"].config.base_url == "https://test.example.com/"
    assert config.environments["TEST"].auth.login == "test-dummy"
    assert config.environments["TEST"].auth.password.get_secret_value() == "00000000001111111111222222222233"


def test_config_file_when_non_existent_default(data_no_auth):
    data_no_auth["GENERAL"]["default_config"] = "TEST"
    with pytest.raises(ValueError):
        ConfigFile.model_validate(data_no_auth)


def test_get_selected_config_env_when_explicit(config_with_auth):
    assert config_with_auth.get_selected_config_env("MYTESTENV") == "MYTESTENV"


def test_get_selected_config_env_when_env_var(config_with_auth, monkeypatch):
    monkeypatch.setenv("BFABRICPY_CONFIG_ENV", "MYTESTENV")
    assert config_with_auth.get_selected_config_env(None) == "MYTESTENV"


def test_get_selected_config_env_when_default(config_with_auth, monkeypatch):
    monkeypatch.delenv("BFABRICPY_CONFIG_ENV", raising=False)
    assert config_with_auth.get_selected_config_env(None) == "PRODUCTION"


def test_get_selected_config(config_with_auth, mocker):
    mock_get_config_env = mocker.patch.object(ConfigFile, "get_selected_config_env", return_value="PRODUCTION")
    assert config_with_auth.get_selected_config() == config_with_auth.environments["PRODUCTION"]
    mock_get_config_env.assert_called_once_with(explicit_config_env=None)


def test_reject_env_name_default(mocker, data_no_auth):
    data_no_auth["default"] = {"base_url": "https://example.com"}
    with pytest.raises(ValueError) as error:
        ConfigFile.model_validate(data_no_auth)
    assert "Environment name 'default' is reserved." in str(error.value)


class TestConfigNoDefault:
    @staticmethod
    @pytest.fixture()
    def config_data():
        return {
            "GENERAL": {},
            "PRODUCTION": {
                "base_url": "https://example.com",
            },
        }

    @staticmethod
    @pytest.fixture()
    def config(config_data):
        return ConfigFile.model_validate(config_data)

    @staticmethod
    def test_validate(config):
        assert config.general.default_config is None
        assert config.environments["PRODUCTION"].config.base_url == "https://example.com/"

    @staticmethod
    def test_get_selected_config_env(config):
        with pytest.raises(ValueError) as error:
            config.get_selected_config_env(None)
        assert "No environment was specified and no default environment was found." in str(error.value)

    @staticmethod
    def test_get_selected_config_env_when_env_var(config, mocker):
        mocker.patch.dict(os.environ, {"BFABRICPY_CONFIG_ENV": "PRODUCTION"})
        assert config.get_selected_config_env(None) == "PRODUCTION"

    @staticmethod
    def test_get_selected_config_env_when_explicit(config):
        assert config.get_selected_config_env("PRODUCTION") == "PRODUCTION"


class TestReadConfig:
    @pytest.fixture
    def example_config_path(self) -> Path:
        return Path(__file__).parent / "example_config.yml"

    def test_bypath_all_fields(self, example_config_path: Path) -> None:
        config, auth = read_config_file(example_config_path, config_env="TEST")
        applications_dict_ground_truth = {
            "Proteomics/CAT_123": 7,
            "Proteomics/DOG_552": 6,
            "Proteomics/DUCK_666": 12,
        }

        job_notification_emails_ground_truth = "user1@example.com user2@example.com"

        assert auth.login == "testuser"
        assert auth.password.get_secret_value() == "012345678901234567890123456789ff"
        assert config.base_url == "https://test-server.example.com/api/"
        assert config.application_ids == applications_dict_ground_truth
        assert config.job_notification_emails == job_notification_emails_ground_truth

    def test_when_empty_optional(self, example_config_path: Path, logot: Logot) -> None:
        config, auth = read_config_file(example_config_path, config_env="STANDBY")
        assert auth is None
        assert config.base_url == "https://standby-server.example.com/api/"
        assert config.application_ids == {}
        assert config.job_notification_emails == ""
        logot.assert_logged(
            logged.debug(f"Reading configuration from: {str(example_config_path.absolute())} config_env='STANDBY'")
        )


class TestEnvironmentConfigOAuth:
    def test_auth_method_oauth(self):
        config = EnvironmentConfig.model_validate(
            {
                "base_url": "https://example.com",
                "auth_method": "oauth",
                "client_id": "my-app",
            }
        )
        assert config.auth_method == "oauth"
        assert config.client_id == "my-app"
        assert config.auth is None

    def test_auth_method_not_in_client_config(self):
        """auth_method and client_id should not leak into BfabricClientConfig."""
        config = EnvironmentConfig.model_validate(
            {
                "base_url": "https://example.com",
                "auth_method": "oauth",
                "client_id": "my-app",
            }
        )
        assert not hasattr(config.config, "auth_method")
        assert not hasattr(config.config, "client_id")

    def test_scope_binds(self):
        config = EnvironmentConfig.model_validate(
            {
                "base_url": "https://example.com",
                "auth_method": "oauth",
                "client_id": "my-app",
                "scope": "api:write tus",
            }
        )
        assert config.scope == "api:write tus"

    def test_scope_not_in_client_config(self):
        config = EnvironmentConfig.model_validate(
            {"base_url": "https://example.com", "auth_method": "oauth", "scope": "api:read"}
        )
        assert not hasattr(config.config, "scope")

    def test_scope_absent_defaults_to_none(self):
        """An environment written by 1.16.0 has no ``scope`` key; it must still load."""
        config = EnvironmentConfig.model_validate({"base_url": "https://example.com", "auth_method": "oauth"})
        assert config.scope is None

    def test_backward_compat_without_oauth_fields(self):
        config = EnvironmentConfig.model_validate(
            {
                "base_url": "https://example.com",
                "login": "user",
                "password": "x" * 32,
            }
        )
        assert config.auth_method is None
        assert config.client_id is None
        assert config.auth is not None


if __name__ == "__main__":
    pytest.main()


class TestClientCredentialsEnvironment:
    """A service-account environment: ``client_credentials`` with an inline ``client_secret``."""

    def test_parses_client_credentials_environment(self):
        config = ConfigFile.model_validate(
            {
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": "https://example.com/bfabric",
                    "auth_method": "client_credentials",
                    "client_id": "sysadmin-cron",
                    "client_secret": "s3cret",
                    "scope": "read-write",
                },
            }
        )
        env = config.environments["PROD"]
        assert env.auth_method == "client_credentials"
        assert env.client_id == "sysadmin-cron"
        assert env.client_secret is not None
        assert env.client_secret.get_secret_value() == "s3cret"

    def test_client_secret_is_not_leaked_into_client_config(self):
        # ``client_secret`` is auth-owned; it must not fall through into BfabricClientConfig's extras.
        config = ConfigFile.model_validate(
            {
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": "https://example.com/bfabric",
                    "auth_method": "client_credentials",
                    "client_id": "cron",
                    "client_secret": "s3cret",
                },
            }
        )
        assert "client_secret" not in config.environments["PROD"].config.model_dump()

    def test_client_secret_is_not_leaked_by_repr(self):
        config = ConfigFile.model_validate(
            {
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": "https://example.com/bfabric",
                    "auth_method": "client_credentials",
                    "client_id": "cron",
                    "client_secret": "s3cret",
                },
            }
        )
        assert "s3cret" not in repr(config.environments["PROD"])


class TestRegistrationCredentials:
    """RFC 7591 registration credentials, kept so a misconfigured client can be edited later."""

    def test_parses_registration_fields(self):
        config = ConfigFile.model_validate(
            {
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": "https://example.com/bfabric",
                    "auth_method": "client_credentials",
                    "client_id": "cron",
                    "client_secret": "s3cret",
                    "registration_access_token": "reg-tok",
                    "registration_client_uri": "https://example.com/bfabric/rest/oauth/register/cron",
                },
            }
        )
        env = config.environments["PROD"]
        assert env.registration_access_token is not None
        assert env.registration_access_token.get_secret_value() == "reg-tok"
        assert env.registration_client_uri == "https://example.com/bfabric/rest/oauth/register/cron"

    def test_registration_fields_do_not_leak_into_client_config(self):
        config = ConfigFile.model_validate(
            {
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": "https://example.com/bfabric",
                    "auth_method": "client_credentials",
                    "client_id": "cron",
                    "client_secret": "s3cret",
                    "registration_access_token": "reg-tok",
                    "registration_client_uri": "https://example.com/bfabric/rest/oauth/register/cron",
                },
            }
        )
        dumped = config.environments["PROD"].config.model_dump()
        assert "registration_access_token" not in dumped
        assert "registration_client_uri" not in dumped

    def test_registration_token_is_not_leaked_by_repr(self):
        config = ConfigFile.model_validate(
            {
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": "https://example.com/bfabric",
                    "auth_method": "client_credentials",
                    "client_id": "cron",
                    "registration_access_token": "reg-tok",
                },
            }
        )
        assert "reg-tok" not in repr(config.environments["PROD"])

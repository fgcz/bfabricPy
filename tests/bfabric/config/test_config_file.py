import os
from pathlib import Path

import pytest
from logot import logged, Logot

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

        job_notification_emails_ground_truth = "john.snow@fgcz.uzh.ch billy.the.kid@fgcz.ethz.ch"

        assert auth.login == "my_epic_test_login"
        assert auth.password.get_secret_value() == "012345678901234567890123456789ff"
        assert config.base_url == "https://mega-test-server.uzh.ch/mytest"
        assert config.application_ids == applications_dict_ground_truth
        assert config.job_notification_emails == job_notification_emails_ground_truth

    def test_when_empty_optional(self, example_config_path: Path, logot: Logot) -> None:
        config, auth = read_config_file(example_config_path, config_env="STANDBY")
        assert auth is None
        assert config.base_url == "https://standby-server.uzh.ch/mystandby"
        assert config.application_ids == {}
        assert config.job_notification_emails == ""
        logot.assert_logged(
            logged.debug(f"Reading configuration from: {str(example_config_path.absolute())} config_env='STANDBY'")
        )


if __name__ == "__main__":
    pytest.main()

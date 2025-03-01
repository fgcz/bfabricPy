import pytest

from bfabric.config.config_file import ConfigFile, GeneralConfig, EnvironmentConfig


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


if __name__ == "__main__":
    pytest.main()

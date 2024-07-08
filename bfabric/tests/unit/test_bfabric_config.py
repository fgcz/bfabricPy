import os
from pathlib import Path

import pytest
from logot import Logot, logged
from pytest_mock import MockerFixture

from bfabric.bfabric_config import BfabricAuth, BfabricConfig, read_config


@pytest.fixture
def mock_config() -> BfabricConfig:
    return BfabricConfig(
        base_url="url",
        application_ids={"app": 1},
    )


@pytest.fixture
def example_config_path() -> Path:
    return Path(__file__).parent / "example_config.yml"


def test_bfabric_auth_repr() -> None:
    assert repr(BfabricAuth("login", "password")) == "BfabricAuth(login='login', password=...)"


def test_bfabric_auth_str() -> None:
    assert str(BfabricAuth("login", "password")) == "BfabricAuth(login='login', password=...)"


def test_bfabric_config_default_params_when_omitted() -> None:
    config = BfabricConfig()
    assert config.base_url == "https://fgcz-bfabric.uzh.ch/bfabric"
    assert config.application_ids == {}
    assert config.job_notification_emails == ""


def test_bfabric_config_default_params_when_specified() -> None:
    config = BfabricConfig(base_url=None, application_ids=None, job_notification_emails=None)
    assert config.base_url == "https://fgcz-bfabric.uzh.ch/bfabric"
    assert config.application_ids == {}
    assert config.job_notification_emails == ""


def test_bfabric_config_copy_with_overrides(mock_config: BfabricConfig) -> None:
    new_config = mock_config.copy_with(
        base_url="new_url",
        application_ids={"new": 2},
    )
    assert new_config.base_url == "new_url"
    assert new_config.application_ids == {"new": 2}
    assert mock_config.base_url == "url"
    assert mock_config.application_ids == {"app": 1}


def test_bfabric_config_copy_with_replaced_when_none(mock_config: BfabricConfig) -> None:
    new_config = mock_config.copy_with(base_url=None, application_ids=None)
    assert new_config.base_url == "url"
    assert new_config.application_ids == {"app": 1}
    assert mock_config.base_url == "url"
    assert mock_config.application_ids == {"app": 1}


def test_bfabric_config_read_yml_bypath_default(mocker: MockerFixture, example_config_path: Path, logot: Logot) -> None:
    # Ensure environment variable is not available, and the default is environment is loaded
    mocker.patch.dict(os.environ, {}, clear=True)

    config, auth = read_config(example_config_path)
    assert auth.login == "my_epic_production_login"
    assert auth.password == "my_secret_production_password"
    assert config.base_url == "https://mega-production-server.uzh.ch/myprod"

    logot.assert_logged(logged.info(f"Reading configuration from: {str(example_config_path.absolute())}"))
    logot.assert_logged(logged.info("BFABRICPY_CONFIG_ENV not found, using default environment PRODUCTION"))


def test_bfabric_config_read_yml_bypath_environment_variable(
    mocker: MockerFixture, example_config_path: Path, logot: Logot
) -> None:
    # Explicitly set the environment variable for this process
    mocker.patch.dict(os.environ, {"BFABRICPY_CONFIG_ENV": "TEST"}, clear=True)

    config, auth = read_config(example_config_path)
    assert auth.login == "my_epic_test_login"
    assert auth.password == "my_secret_test_password"
    assert config.base_url == "https://mega-test-server.uzh.ch/mytest"

    logot.assert_logged(logged.info(f"Reading configuration from: {str(example_config_path.absolute())}"))
    logot.assert_logged(logged.info("found BFABRICPY_CONFIG_ENV = TEST"))


def test_read_yml_bypath_all_fields(example_config_path: Path) -> None:
    config, auth = read_config(example_config_path, config_env="TEST")
    applications_dict_ground_truth = {
        "Proteomics/CAT_123": 7,
        "Proteomics/DOG_552": 6,
        "Proteomics/DUCK_666": 12,
    }

    job_notification_emails_ground_truth = "john.snow@fgcz.uzh.ch billy.the.kid@fgcz.ethz.ch"

    assert auth.login == "my_epic_test_login"
    assert auth.password == "my_secret_test_password"
    assert config.base_url == "https://mega-test-server.uzh.ch/mytest"
    assert config.application_ids == applications_dict_ground_truth
    assert config.job_notification_emails == job_notification_emails_ground_truth


def test_read_yml_when_empty_optional(example_config_path: Path, logot: Logot) -> None:
    config, auth = read_config(example_config_path, config_env="STANDBY")
    assert auth is None
    assert config.base_url == "https://standby-server.uzh.ch/mystandby"
    assert config.application_ids == {}
    assert config.job_notification_emails == ""
    logot.assert_logged(logged.info(f"Reading configuration from: {str(example_config_path.absolute())}"))


def test_repr(mock_config: BfabricConfig) -> None:
    rep = repr(mock_config)
    assert rep == "BfabricConfig(base_url='url', application_ids={'app': 1}, job_notification_emails='')"


def test_str(mock_config: BfabricConfig) -> None:
    rep = str(mock_config)
    assert rep == "BfabricConfig(base_url='url', application_ids={'app': 1}, job_notification_emails='')"


if __name__ == "__main__":
    pytest.main()

import os
from pathlib import Path

import pytest
from logot import Logot, logged
from pytest_mock import MockerFixture

from bfabric.bfabric_config import read_config
from bfabric.config import BfabricClientConfig


@pytest.fixture
def mock_config() -> BfabricClientConfig:
    return BfabricClientConfig(
        base_url="https://example.com",
        application_ids={"app": 1},
    )


@pytest.fixture
def example_config_path() -> Path:
    return Path(__file__).parents[1] / "example_config.yml"


def test_bfabric_config_default_params_when_omitted() -> None:
    config = BfabricClientConfig()
    assert config.base_url == "https://fgcz-bfabric.uzh.ch/bfabric"
    assert config.application_ids == {}
    assert config.job_notification_emails == ""


def test_bfabric_config_default_params_when_specified() -> None:
    config = BfabricClientConfig(base_url=None, application_ids=None, job_notification_emails=None)
    assert config.base_url == "https://fgcz-bfabric.uzh.ch/bfabric"
    assert config.application_ids == {}
    assert config.job_notification_emails == ""


def test_bfabric_config_copy_with_overrides(mock_config: BfabricClientConfig) -> None:
    new_config = mock_config.copy_with(
        base_url="https://example.com/new-url",
        application_ids={"new": 2},
    )
    assert new_config.base_url == "https://example.com/new-url"
    assert new_config.application_ids == {"new": 2}
    assert mock_config.base_url == "https://example.com/"
    assert mock_config.application_ids == {"app": 1}


def test_bfabric_config_copy_with_replaced_when_none(
    mock_config: BfabricClientConfig,
) -> None:
    new_config = mock_config.copy_with(base_url=None, application_ids=None)
    assert new_config.base_url == "https://example.com/"
    assert new_config.application_ids == {"app": 1}
    assert mock_config.base_url == "https://example.com/"
    assert mock_config.application_ids == {"app": 1}


def test_bfabric_config_copy_with_replaced_when_invalid(
    mock_config: BfabricClientConfig,
) -> None:
    with pytest.raises(ValueError):
        mock_config.copy_with(base_url="not a url")


def test_bfabric_config_read_yml_bypath_default(mocker: MockerFixture, example_config_path: Path, logot: Logot) -> None:
    # Ensure environment variable is not available, and the default is environment is loaded
    mocker.patch.dict(os.environ, {}, clear=True)

    config, auth = read_config(example_config_path)
    assert auth.login == "my_epic_production_login"
    assert auth.password.get_secret_value() == "01234567890123456789012345678901"
    assert config.base_url == "https://mega-production-server.uzh.ch/myprod"

    logot.assert_logged(logged.debug(f"Reading configuration from: {str(example_config_path.absolute())}"))
    logot.assert_logged(logged.debug("BFABRICPY_CONFIG_ENV not found, using default environment PRODUCTION"))


def test_bfabric_config_read_yml_bypath_environment_variable(
    mocker: MockerFixture, example_config_path: Path, logot: Logot
) -> None:
    # Explicitly set the environment variable for this process
    mocker.patch.dict(os.environ, {"BFABRICPY_CONFIG_ENV": "TEST"}, clear=True)

    config, auth = read_config(example_config_path)
    assert auth.login == "my_epic_test_login"
    assert auth.password.get_secret_value() == "012345678901234567890123456789ff"
    assert config.base_url == "https://mega-test-server.uzh.ch/mytest"

    logot.assert_logged(logged.debug(f"Reading configuration from: {str(example_config_path.absolute())}"))
    logot.assert_logged(logged.debug("found BFABRICPY_CONFIG_ENV = TEST"))


def test_repr(mock_config: BfabricClientConfig) -> None:
    rep = repr(mock_config)
    assert rep == (
        "BfabricClientConfig(base_url='https://example.com/', application_ids={'app': 1}, job_notification_emails='',"
        " engine=<BfabricAPIEngineType.SUDS: 'SUDS'>)"
    )


def test_str(mock_config: BfabricClientConfig) -> None:
    rep = str(mock_config)
    print(rep)
    assert rep == (
        "BfabricClientConfig(base_url='https://example.com/', application_ids={'app': 1}, job_notification_emails='',"
        " engine=<BfabricAPIEngineType.SUDS: 'SUDS'>)"
    )


if __name__ == "__main__":
    pytest.main()

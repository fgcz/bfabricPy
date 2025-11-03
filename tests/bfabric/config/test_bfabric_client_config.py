import os
from pathlib import Path

import pytest
from logot import Logot, logged
from pydantic import ValidationError
from pytest_mock import MockerFixture

from bfabric.config import BfabricClientConfig
from bfabric.config.config_file import read_config_file


@pytest.fixture
def mock_config() -> BfabricClientConfig:
    return BfabricClientConfig(
        base_url="https://example.com",
        application_ids={"app": 1},
    )


@pytest.fixture
def example_config_path() -> Path:
    return Path(__file__).parent / "example_config.yml"


class TestDefaultParams:
    def test_when_omitted(self):
        config = BfabricClientConfig(base_url="https://fgcz-bfabric.uzh.ch/bfabric")
        assert config.application_ids == {}
        assert config.job_notification_emails == ""

    def test_base_url_is_required(self):
        with pytest.raises(ValidationError) as error:
            BfabricClientConfig()

        assert error.value.error_count() == 1
        assert error.value.errors()[0]["loc"] == ("base_url",)


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

    config, auth = read_config_file(example_config_path)
    assert auth.login == "my_epic_production_login"
    assert auth.password.get_secret_value() == "01234567890123456789012345678901"
    assert config.base_url == "https://mega-production-server.uzh.ch/myprod"

    logot.assert_logged(
        logged.debug(f"Reading configuration from: {str(example_config_path.absolute())} config_env=None")
    )
    logot.assert_logged(logged.debug("BFABRICPY_CONFIG_ENV not found, using default environment PRODUCTION"))


def test_bfabric_config_read_yml_bypath_environment_variable(
    mocker: MockerFixture, example_config_path: Path, logot: Logot
) -> None:
    # Explicitly set the environment variable for this process
    mocker.patch.dict(os.environ, {"BFABRICPY_CONFIG_ENV": "TEST"}, clear=True)

    config, auth = read_config_file(example_config_path)
    assert auth.login == "my_epic_test_login"
    assert auth.password.get_secret_value() == "012345678901234567890123456789ff"
    assert config.base_url == "https://mega-test-server.uzh.ch/mytest"

    logot.assert_logged(
        logged.debug(f"Reading configuration from: {str(example_config_path.absolute())} config_env=None")
    )
    logot.assert_logged(logged.debug("found BFABRICPY_CONFIG_ENV = TEST"))


@pytest.mark.parametrize("variant", [repr, str])
def test_repr(mock_config: BfabricClientConfig, variant) -> None:
    rep = variant(mock_config)
    assert rep == (
        "BfabricClientConfig(base_url='https://example.com/', application_ids={'app': 1}, job_notification_emails='',"
        " engine=BfabricAPIEngineType.SUDS)"
    )


if __name__ == "__main__":
    pytest.main()

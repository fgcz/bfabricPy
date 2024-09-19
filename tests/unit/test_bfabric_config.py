from pathlib import Path

import pytest
from logot import Logot, logged

from bfabric.bfabric_config import read_config


@pytest.fixture
def example_config_path() -> Path:
    return Path(__file__).parent / "example_config.yml"


def test_read_yml_bypath_all_fields(example_config_path: Path) -> None:
    config, auth = read_config(example_config_path, config_env="TEST")
    applications_dict_ground_truth = {
        "Proteomics/CAT_123": 7,
        "Proteomics/DOG_552": 6,
        "Proteomics/DUCK_666": 12,
    }

    job_notification_emails_ground_truth = "john.snow@fgcz.uzh.ch billy.the.kid@fgcz.ethz.ch"

    assert auth.login == "my_epic_test_login"
    assert auth.password == "012345678901234567890123456789ff"
    assert config.base_url == "https://mega-test-server.uzh.ch/mytest"
    assert config.application_ids == applications_dict_ground_truth
    assert config.job_notification_emails == job_notification_emails_ground_truth


def test_read_yml_when_empty_optional(example_config_path: Path, logot: Logot) -> None:
    config, auth = read_config(example_config_path, config_env="STANDBY")
    assert auth is None
    assert config.base_url == "https://standby-server.uzh.ch/mystandby"
    assert config.application_ids == {}
    assert config.job_notification_emails == ""
    logot.assert_logged(logged.debug(f"Reading configuration from: {str(example_config_path.absolute())}"))


if __name__ == "__main__":
    pytest.main()

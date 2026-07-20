import os
import pytest
from loguru import logger


def pytest_runtest_setup() -> None:
    # This reduces the risk that someone runs unit tests, using their real BFabric credentials.
    os.environ["BFABRICPY_CONFIG_ENV"] = "__MOCK"


@pytest.fixture(autouse=True)
def _enable_bfabric_logging() -> None:
    # bfabric calls logger.disable("bfabric") at import (loguru's library convention), which filters
    # its records before they reach any sink -- including logot's capturer. Re-enable per test so
    # logot.assert_logged works regardless of random test order.
    logger.enable("bfabric")


@pytest.fixture
def bfabric_instance() -> str:
    return "https://bfabric.example.org/bfabric/"

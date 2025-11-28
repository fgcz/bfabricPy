import os
import pytest


def pytest_runtest_setup() -> None:
    # This reduces the risk that someone runs unit tests, using their real BFabric credentials.
    os.environ["BFABRICPY_CONFIG_ENV"] = "__MOCK"


@pytest.fixture
def bfabric_instance() -> str:
    return "https://bfabric.example.org/bfabric/"

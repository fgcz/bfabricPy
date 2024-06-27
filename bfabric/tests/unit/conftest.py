import os


def pytest_runtest_setup() -> None:
    # This reduces the risk that someone runs unit tests, using their real BFabric credentials.
    os.environ["BFABRICPY_CONFIG_ENV"] = "__MOCK"

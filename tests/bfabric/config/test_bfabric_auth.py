from pathlib import Path

import pytest

from bfabric.config import BfabricAuth


@pytest.fixture
def example_config_path() -> Path:
    return Path(__file__).parent / "example_config.yml"


def test_bfabric_auth_repr() -> None:
    assert repr(BfabricAuth(login="login", password="x" * 32)) == "BfabricAuth(login='login', password=...)"


def test_bfabric_auth_str() -> None:
    assert str(BfabricAuth(login="login", password="x" * 32)) == "BfabricAuth(login='login', password=...)"


if __name__ == "__main__":
    pytest.main()

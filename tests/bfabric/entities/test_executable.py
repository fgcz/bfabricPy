import pytest
from bfabric.entities.executable import Executable


@pytest.fixture
def data_dict() -> dict[str, str | int]:
    return {
        "classname": "executable",
        "id": 1234,
        "base64": "SGVsbG8gd29ybGQ=",
    }


@pytest.fixture
def executable(data_dict: dict[str, str | int], bfabric_instance: str) -> Executable:
    return Executable(data_dict, client=None, bfabric_instance=bfabric_instance)


def test_decoded_bytes(executable):
    assert executable.decoded_bytes == b"Hello world"


def test_decoded_str(executable):
    assert executable.decoded_str == "Hello world"

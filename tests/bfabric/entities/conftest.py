import pytest

from bfabric import Bfabric


@pytest.fixture
def mock_client(mocker, bfabric_instance):
    return mocker.MagicMock(spec=Bfabric, config=mocker.MagicMock(base_url=bfabric_instance))

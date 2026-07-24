import pytest

from bfabric import Bfabric


@pytest.fixture
def mock_client(mocker, bfabric_instance):
    return mocker.MagicMock(spec=Bfabric, config=mocker.MagicMock(base_url=bfabric_instance))


@pytest.fixture
def mock_read_scope(mocker):
    """Install a mock ``ReadScope`` as the ambient read scope.

    Lazy entity navigation (unloaded refs, ``created_by``, ``ExternalJob.client_entity``) resolves the
    connection via ``get_read_scope()``; patching it here lets tests drive ``read_uris`` / ``read_id`` /
    ``query_one`` return values and assert on the calls.
    """
    read_scope = mocker.MagicMock(name="ReadScope")
    mocker.patch("bfabric.entities.core.read_scope.get_read_scope", return_value=read_scope)
    return read_scope

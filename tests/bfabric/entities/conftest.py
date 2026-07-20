import pytest

from bfabric import Bfabric


@pytest.fixture
def mock_client(mocker, bfabric_instance):
    return mocker.MagicMock(spec=Bfabric, config=mocker.MagicMock(base_url=bfabric_instance))


@pytest.fixture
def mock_session(mocker):
    """Install a mock ``BfabricSession`` as the ambient session.

    Lazy entity navigation (unloaded refs, ``created_by``, ``ExternalJob.client_entity``) resolves the
    connection via ``get_session()``; patching it here lets tests drive ``read_uris`` / ``read_id`` /
    ``query_one`` return values and assert on the calls.
    """
    session = mocker.MagicMock(name="BfabricSession")
    mocker.patch("bfabric.entities.core.session.get_session", return_value=session)
    return session

import pytest

from bfabric.entities.core.entity_reader import EntityReader
from bfabric.entities.core.users import Users


@pytest.fixture
def entity_reader(mocker):
    return mocker.MagicMock(spec=EntityReader, autospec=True, name="entity_reader")


@pytest.fixture
def users(entity_reader):
    return Users(entity_reader=entity_reader)


def test_get_by_id(entity_reader, users, bfabric_instance):
    entity_reader.read_id.return_value = "mocked_user"
    assert "mocked_user" not in users._users
    user = users.get_by_id(bfabric_instance, id=100)
    assert user == "mocked_user"
    entity_reader.read_id.assert_called_once_with(entity_type="user", entity_id=100, bfabric_instance=bfabric_instance)
    assert "mocked_user" in users._users


def test_get_by_login(entity_reader, users, bfabric_instance):
    entity_reader.query.return_value = {"mocked_uri": "mocked_user"}
    assert "mocked_user" not in users._users
    user = users.get_by_login(bfabric_instance, login="testuser")
    assert user == "mocked_user"
    entity_reader.query.assert_called_once_with(
        entity_type="user", obj={"login": "testuser"}, bfabric_instance=bfabric_instance, max_results=1
    )
    assert "mocked_user" in users._users

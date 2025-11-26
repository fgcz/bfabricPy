import pytest

from bfabric.entities.core.entity_reader import EntityReader
from bfabric.entities.core.users import Users


@pytest.fixture
def entity_reader(mocker):
    return mocker.MagicMock(spec=EntityReader, autospec=True, name="entity_reader")


@pytest.fixture
def users(entity_reader):
    return Users(entity_reader=entity_reader)


@pytest.fixture
def mock_user(mocker):
    data_dict = {"id": 100, "login": "testuser"}
    user = mocker.MagicMock(name="mock_user", id=100, spec=["id", "__getitem__"])
    user.__getitem__.side_effect = data_dict.__getitem__
    return user


class TestGetById:
    @staticmethod
    def test_not_cached(entity_reader, users, bfabric_instance, mock_user):
        entity_reader.read_id.return_value = mock_user
        assert mock_user not in users._users
        user = users.get_by_id(bfabric_instance, id=100)
        assert user is mock_user
        entity_reader.read_id.assert_called_once_with(
            entity_type="user", entity_id=100, bfabric_instance=bfabric_instance
        )
        assert mock_user in users._users

    @staticmethod
    def test_cached(entity_reader, users, bfabric_instance, mock_user):
        users._users.append(mock_user)
        user = users.get_by_id(bfabric_instance, id=100)
        assert user is mock_user
        entity_reader.read_id.assert_not_called()


class TestGetByName:
    @staticmethod
    def test_not_cached(entity_reader, users, bfabric_instance, mock_user):
        entity_reader.query.return_value = {"mocked_uri": mock_user}
        assert mock_user not in users._users
        user = users.get_by_login(bfabric_instance, login="testuser")
        assert user is mock_user
        entity_reader.query.assert_called_once_with(
            entity_type="user", obj={"login": "testuser"}, bfabric_instance=bfabric_instance, max_results=1
        )
        assert mock_user in users._users

    @staticmethod
    def test_cached(entity_reader, users, bfabric_instance, mock_user):
        users._users.append(mock_user)
        user = users.get_by_login(bfabric_instance, login="testuser")
        assert user is mock_user
        entity_reader.query.assert_not_called()

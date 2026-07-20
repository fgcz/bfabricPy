import pytest

from bfabric.entities.core.users import Users


@pytest.fixture
def users():
    return Users()


@pytest.fixture
def mock_user(mocker):
    data_dict = {"id": 100, "login": "testuser"}
    user = mocker.MagicMock(name="mock_user", id=100, spec=["id", "__getitem__"])
    user.__getitem__.side_effect = data_dict.__getitem__
    return user


class TestGetById:
    @staticmethod
    def test_not_cached(mock_session, users, bfabric_instance, mock_user):
        from bfabric.entities.user import User as UserEntity

        mock_session.read_id.return_value = mock_user
        assert mock_user not in users._users
        user = users.get_by_id(bfabric_instance, id=100)
        assert user is mock_user
        mock_session.read_id.assert_called_once_with(UserEntity, 100, bfabric_instance=bfabric_instance)
        assert mock_user in users._users

    @staticmethod
    def test_cached(mock_session, users, bfabric_instance, mock_user):
        users._users.append(mock_user)
        user = users.get_by_id(bfabric_instance, id=100)
        assert user is mock_user
        mock_session.read_id.assert_not_called()


class TestGetByName:
    @staticmethod
    def test_not_cached(mock_session, users, bfabric_instance, mock_user):
        from bfabric.entities.user import User as UserEntity

        mock_session.query_one.return_value = mock_user
        assert mock_user not in users._users
        user = users.get_by_login(bfabric_instance, login="testuser")
        assert user is mock_user
        mock_session.query_one.assert_called_once_with(
            UserEntity, {"login": "testuser"}, bfabric_instance=bfabric_instance
        )
        assert mock_user in users._users

    @staticmethod
    def test_cached(mock_session, users, bfabric_instance, mock_user):
        users._users.append(mock_user)
        user = users.get_by_login(bfabric_instance, login="testuser")
        assert user is mock_user
        mock_session.query_one.assert_not_called()

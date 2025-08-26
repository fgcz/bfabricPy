import pytest

from bfabric import Bfabric
from bfabric.entities import User
from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_user import HasUser


class MockEntity(Entity):
    def __init__(self, data_dict=None, client=None):
        super().__init__(data_dict=data_dict, client=client)


@pytest.fixture()
def mock_client(mocker):
    return mocker.MagicMock(name="mock_client", spec=Bfabric)


def test_init():
    has_user = HasUser(bfabric_field="user_field")
    assert has_user._entity_type is User
    assert has_user._bfabric_field == "user_field"
    assert has_user._optional == False


def test_init_optional():
    has_user = HasUser(bfabric_field="user_field", optional=True)
    assert has_user._entity_type is User
    assert has_user._bfabric_field == "user_field"
    assert has_user._optional == True


def test_get_some_when_cache_not_exists(mocker, mock_client):
    mock_obj = MockEntity(data_dict={"user_field": "mock_login"}, client=mock_client)
    has_user = HasUser(bfabric_field="user_field")
    mock_load_user = mocker.patch.object(HasUser, "_load_user", return_value="mock_user")
    result = has_user.__get__(mock_obj)
    assert result == "mock_user"
    mock_load_user.assert_called_once_with(obj=mock_obj)
    assert hasattr(mock_obj, "_HasUser__user_field_cache")
    assert getattr(mock_obj, "_HasUser__user_field_cache") == "mock_user"


def test_get_some_when_cache_exists(mocker, mock_client):
    mock_obj = MockEntity(data_dict={"user_field": "mock_login"}, client=mock_client)
    has_user = HasUser(bfabric_field="user_field")
    mock_obj._HasUser__user_field_cache = "mock_user"
    mock_load_user = mocker.patch.object(HasUser, "_load_user", return_value="mock_user")
    result = has_user.__get__(mock_obj)
    assert result == "mock_user"
    mock_load_user.assert_not_called()


def test_load_user_found(mocker, mock_client):
    mock_obj = MockEntity(data_dict={"user_field": "mock_login"}, client=mock_client)
    has_user = HasUser(bfabric_field="user_field")
    mock_user = mocker.MagicMock(name="mock_user", spec=User)
    mock_find_by_login = mocker.patch.object(User, "find_by_login", return_value=mock_user)
    result = has_user._load_user(obj=mock_obj)
    assert result == mock_user
    mock_find_by_login.assert_called_once_with(login="mock_login", client=mock_client)


def test_load_user_not_found_required(mocker, mock_client):
    mock_obj = MockEntity(data_dict={"user_field": "mock_login"}, client=mock_client)
    has_user = HasUser(bfabric_field="user_field")
    mock_find_by_login = mocker.patch.object(User, "find_by_login", return_value=None)
    with pytest.raises(ValueError) as exc_info:
        has_user._load_user(obj=mock_obj)
    assert str(exc_info.value) == "Field 'user_field' is required"
    mock_find_by_login.assert_called_once_with(login="mock_login", client=mock_client)


def test_load_user_not_found_optional(mocker, mock_client):
    mock_obj = MockEntity(data_dict={"user_field": "mock_login"}, client=mock_client)
    has_user = HasUser(bfabric_field="user_field", optional=True)
    mock_find_by_login = mocker.patch.object(User, "find_by_login", return_value=None)
    result = has_user._load_user(obj=mock_obj)
    assert result is None
    mock_find_by_login.assert_called_once_with(login="mock_login", client=mock_client)

import datetime
import pytest

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.mixins.user_created_mixin import UserCreatedMixin
from bfabric.entities.core.users import Users


class MockEntity(Entity, UserCreatedMixin):
    pass


@pytest.fixture()
def data_dict():
    return {
        "created": "2024-01-01T12:00:00Z",
        "modified": "2024-01-02T12:00:00Z",
        "createdby": "creator_login",
        "modifiedby": "modifier_login",
    }


@pytest.fixture
def entity(data_dict, mock_client, bfabric_instance):
    return MockEntity(data_dict=data_dict, client=mock_client, bfabric_instance=bfabric_instance)


@pytest.fixture
def user_creator(mocker):
    return mocker.MagicMock(name="user_creator")


@pytest.fixture
def user_modifier(mocker):
    return mocker.MagicMock(name="user_modifier")


@pytest.fixture
def mock_get_by_login(mocker, user_creator, user_modifier):
    def _mock_fn(bfabric_instance: str, login: str):
        if login == "creator_login":
            return user_creator
        elif login == "modifier_login":
            return user_modifier
        return None

    return mocker.patch.object(Users, "get_by_login", side_effect=_mock_fn)


def test_created_at(entity):
    assert entity.created_at == datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)


def test_modified_at(entity):
    assert entity.modified_at == datetime.datetime(2024, 1, 2, 12, 0, 0, tzinfo=datetime.timezone.utc)


def test_created_by(entity, user_creator, mock_get_by_login, bfabric_instance):
    assert entity.created_by == user_creator
    mock_get_by_login.assert_called_once_with(bfabric_instance=bfabric_instance, login="creator_login")


def test_modified_by(entity, user_modifier, mock_get_by_login, bfabric_instance):
    assert entity.modified_by == user_modifier
    mock_get_by_login.assert_called_with(bfabric_instance=bfabric_instance, login="modifier_login")

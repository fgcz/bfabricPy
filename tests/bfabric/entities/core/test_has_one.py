import pytest

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne


class MockEntity(Entity):
    def __init__(self, data_dict=None, client=None):
        if data_dict is None:
            data_dict = {"mock": "mock"}
        super().__init__(data_dict=data_dict, client=client)


@pytest.fixture(autouse=True)
def mock_entity_resolution(mocker):
    """Mocks the resolution of the MockEntity class, since it is not actually defined in the bfabric.entities module."""
    mocker.patch.object(
        HasOne,
        "_entity_type",
        new_callable=mocker.PropertyMock,
        return_value=MockEntity,
    )


@pytest.fixture()
def mock_client(mocker):
    return mocker.MagicMock(name="mock_client", spec=Bfabric)


def test_init():
    has_one = HasOne("MockEntity", bfabric_field="test_field")
    assert has_one._entity_type == MockEntity
    assert has_one._bfabric_field == "test_field"


def test_get_when_cache_not_exists(mocker, mock_client):
    mock_obj = MockEntity(data_dict={"test_field": {"id": 1}}, client=mock_client)
    has_one = HasOne("MockEntity", bfabric_field="test_field")
    mock_load_entity = mocker.patch.object(HasOne, "_load_entity", return_value="mock_entity")
    result = has_one.__get__(mock_obj)
    assert result == "mock_entity"
    mock_load_entity.assert_called_once_with(obj=mock_obj)


def test_get_when_cache_exists(mocker, mock_client):
    mock_obj = MockEntity(data_dict={"test_field": {"id": 1}}, client=mock_client)
    has_one = HasOne("MockEntity", bfabric_field="test_field")
    mock_obj._HasOne__test_field_cache = "mock_entity"
    mock_load_entity = mocker.patch.object(HasOne, "_load_entity", return_value="mock_entity")
    result = has_one.__get__(mock_obj)
    assert result == "mock_entity"
    mock_load_entity.assert_not_called()


def test_load_entity_found(mocker, mock_client):
    mock_obj = MockEntity(data_dict={"test_field": {"id": 1}}, client=mock_client)
    has_one = HasOne("MockEntity", bfabric_field="test_field")
    mock_entity = mocker.MagicMock(name="mock_entity", spec=MockEntity)
    mock_find = mocker.patch.object(MockEntity, "find", return_value=mock_entity)
    result = has_one._load_entity(obj=mock_obj)
    assert result == mock_entity
    mock_find.assert_called_once_with(id=1, client=mock_client)


def test_load_entity_not_found_required(mocker, mock_client):
    mock_obj = MockEntity(data_dict={"test_field": None}, client=mock_client)
    has_one = HasOne("MockEntity", bfabric_field="test_field", optional=False)
    with pytest.raises(ValueError) as exc_info:
        has_one._load_entity(obj=mock_obj)
    assert str(exc_info.value) == "Field 'test_field' is required"


def test_load_entity_not_found_optional(mocker, mock_client):
    mock_obj = MockEntity(data_dict={"test_field": None}, client=mock_client)
    has_one = HasOne("MockEntity", bfabric_field="test_field", optional=True)
    result = has_one._load_entity(obj=mock_obj)
    assert result is None


if __name__ == "__main__":
    pytest.main()

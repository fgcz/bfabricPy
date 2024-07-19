import pytest
from polars import DataFrame
from pytest_mock import MockerFixture

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_many import HasMany, _HasManyProxy


class MockEntity(Entity):
    def __init__(self, data_dict=None, client=None):
        if data_dict is None:
            data_dict = {"mock": "mock"}
        super().__init__(data_dict=data_dict, client=client)


@pytest.fixture()
def mock_client(mocker):
    return mocker.MagicMock(name="mock_client", spec=Bfabric)


@pytest.fixture()
def mock_proxy(mock_client):
    return _HasManyProxy(MockEntity, [1, 2], mock_client)


def test_has_many_init():
    has_many = HasMany(MockEntity, bfabric_field="test_field")
    assert has_many._entity_type == MockEntity
    assert has_many._bfabric_field == "test_field"
    assert has_many._ids_property is None
    assert has_many._client_property == "_client"


def test_has_many_get(mock_client):
    mock_obj = MockEntity(data_dict={"test_field": [{"id": 1}, {"id": 2}]}, client=mock_client)
    has_many = HasMany(MockEntity, bfabric_field="test_field")

    result = has_many.__get__(mock_obj)

    assert isinstance(result, _HasManyProxy)
    assert result._entity_type == MockEntity
    assert result._ids == [1, 2]
    assert result._client == mock_client


def test_has_many_get_ids_property(mock_client):
    mock_obj = MockEntity(client=mock_client)
    mock_obj.test_ids = [3, 4]
    has_many = HasMany(MockEntity, ids_property="test_ids")

    result = has_many.__get__(mock_obj)

    assert isinstance(result, _HasManyProxy)
    assert result._entity_type == MockEntity
    assert result._ids == [3, 4]
    assert result._client == mock_client


def test_has_many_get_invalid_config():
    has_many = HasMany(MockEntity)
    mock_obj = MockEntity()

    with pytest.raises(ValueError, match="Exactly one of bfabric_field and ids_property must be set"):
        has_many.__get__(mock_obj)


def test_has_many_proxy_init(mock_proxy, mock_client):
    assert mock_proxy._entity_type == MockEntity
    assert mock_proxy._ids == [1, 2]
    assert mock_proxy._client == mock_client
    assert mock_proxy._items == {}


def test_has_many_proxy_ids(mock_proxy):
    assert mock_proxy.ids == [1, 2]


def test_has_many_proxy_list(mocker: MockerFixture, mock_client, mock_proxy):
    mock_entities = {1: MockEntity(), 2: MockEntity()}
    mocker.patch.object(MockEntity, "find_all", return_value=mock_entities)

    result = mock_proxy.list

    assert result == sorted(mock_entities.values(), key=lambda x: mock_entities.keys())
    MockEntity.find_all.assert_called_once_with(ids=[1, 2], client=mock_client)


def test_has_many_proxy_polars(mocker: MockerFixture, mock_client, mock_proxy):
    mock_entities = {1: MockEntity(), 2: MockEntity()}
    mocker.patch.object(MockEntity, "find_all", return_value=mock_entities)
    mocker.patch.object(DataFrame, "__init__", return_value=None)

    result = mock_proxy.polars

    assert isinstance(result, DataFrame)
    DataFrame.__init__.assert_called_once_with([x.data_dict for x in mock_entities.values()])


def test_has_many_proxy_getitem(mocker: MockerFixture, mock_client, mock_proxy):
    mock_entities = {1: MockEntity(), 2: MockEntity()}
    mocker.patch.object(MockEntity, "find_all", return_value=mock_entities)

    result = mock_proxy[1]

    assert result == mock_entities[1]
    MockEntity.find_all.assert_called_once_with(ids=[1, 2], client=mock_client)


def test_has_many_proxy_iter(mocker: MockerFixture, mock_client, mock_proxy):
    mock_entities = {1: MockEntity(), 2: MockEntity()}
    mocker.patch.object(MockEntity, "find_all", return_value=mock_entities)

    result = list(iter(mock_proxy))

    assert result == sorted(mock_entities.values(), key=lambda x: mock_entities.keys())
    MockEntity.find_all.assert_called_once_with(ids=[1, 2], client=mock_client)


def test_has_many_proxy_repr(mocker: MockerFixture, mock_client, mock_proxy):
    assert repr(mock_proxy) == f"_HasManyProxy({MockEntity}, [1, 2], {mock_client})"
    assert str(mock_proxy) == repr(mock_proxy)


if __name__ == "__main__":
    pytest.main()

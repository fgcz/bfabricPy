import pytest

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity


@pytest.fixture
def mock_client(mocker):
    client = mocker.Mock(spec=Bfabric)
    return client


@pytest.fixture
def mock_data_dict():
    return {"id": 1, "name": "Test Entity"}


@pytest.fixture()
def mock_entity(mock_data_dict, mock_client) -> Entity:
    entity = Entity(mock_data_dict, mock_client)
    entity.ENDPOINT = "test_endpoint"
    return entity


def test_endpoint(mock_entity) -> None:
    assert mock_entity.ENDPOINT == "test_endpoint"


def test_data_dict(mock_entity, mock_data_dict) -> None:
    assert mock_entity.data_dict == mock_data_dict


def test_client(mock_entity, mock_client) -> None:
    assert mock_entity._client == mock_client


def test_find_when_found(mocker, mock_client) -> None:
    mock_client.read.return_value = [{"id": 1, "name": "Test Entity"}]
    mocker.patch.object(Entity, "ENDPOINT", new="test_endpoint")
    entity = Entity.find(1, mock_client)
    assert isinstance(entity, Entity)
    assert entity.data_dict == {"id": 1, "name": "Test Entity"}
    mock_client.read.assert_called_once_with("test_endpoint", obj={"id": 1})


def test_find_when_not_found(mocker, mock_client) -> None:
    mock_client.read.return_value = []
    mocker.patch.object(Entity, "ENDPOINT", new="test_endpoint")
    entity = Entity.find(1, mock_client)
    assert entity is None
    mock_client.read.assert_called_once_with("test_endpoint", obj={"id": 1})


def test_find_all_when_all_found(mocker, mock_client) -> None:
    mock_client.read.return_value = [{"id": 1, "name": "Test Entity"}]
    mocker.patch.object(Entity, "ENDPOINT", new="test_endpoint")
    entities = Entity.find_all([1], mock_client)
    assert len(entities) == 1
    assert isinstance(entities[1], Entity)
    assert entities[1].data_dict == {"id": 1, "name": "Test Entity"}
    mock_client.read.assert_called_once_with("test_endpoint", obj={"id": [1]})


def test_find_all_when_not_all_found(mocker, mock_client) -> None:
    mock_client.read.return_value = [{"id": 5, "name": "Test Entity"}]
    mocker.patch.object(Entity, "ENDPOINT", new="test_endpoint")
    entities = Entity.find_all([1, 5], mock_client)
    assert len(entities) == 1
    assert entities[5].data_dict == {"id": 5, "name": "Test Entity"}
    mock_client.read.assert_called_once_with("test_endpoint", obj={"id": [1, 5]})


def test_repr(mock_entity, mock_data_dict) -> None:
    entity = Entity(mock_data_dict, None)
    assert repr(entity) == "Entity({'id': 1, 'name': 'Test Entity'}, client=None)"


def test_str(mock_entity, mock_data_dict) -> None:
    entity = Entity(mock_data_dict, None)
    assert str(entity) == "Entity({'id': 1, 'name': 'Test Entity'}, client=None)"


if __name__ == "__main__":
    pytest.main()

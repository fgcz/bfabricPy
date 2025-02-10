from pathlib import Path

import pytest

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity


@pytest.fixture
def mock_client(mocker):
    return mocker.Mock(spec=Bfabric)


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


def test_find_all_when_empty_list(mock_client) -> None:
    entities = Entity.find_all([], mock_client)
    assert entities == {}
    mock_client.read.assert_not_called()
    mock_client.assert_not_called()


def test_find_by_when_found(mocker, mock_client) -> None:
    mock_client.read.return_value = [{"id": 1, "name": "Test Entity"}]
    mocker.patch.object(Entity, "ENDPOINT", new="test_endpoint")
    entities = Entity.find_by({"id": 1}, mock_client)
    assert len(entities) == 1
    assert isinstance(entities[1], Entity)
    assert entities[1].data_dict == {"id": 1, "name": "Test Entity"}
    mock_client.read.assert_called_once_with("test_endpoint", obj={"id": 1}, max_results=100)


def test_find_by_when_not_found(mocker, mock_client) -> None:
    mock_client.read.return_value = []
    mocker.patch.object(Entity, "ENDPOINT", new="test_endpoint")
    entities = Entity.find_by({"id": 1}, mock_client)
    assert len(entities) == 0
    mock_client.read.assert_called_once_with("test_endpoint", obj={"id": 1}, max_results=100)


def test_dump_yaml(mocker, mock_entity) -> None:
    mock_yaml_dump = mocker.patch("yaml.safe_dump")
    mock_path = mocker.MagicMock(spec=Path)
    mock_entity.dump_yaml(mock_path)
    mock_path.open.assert_called_once_with("w")
    mock_yaml_dump.assert_called_once_with(mock_entity.data_dict, mock_path.open.return_value.__enter__.return_value)


def test_load_yaml(mocker) -> None:
    mock_yaml_load = mocker.patch("yaml.safe_load", return_value={"key": "value"})
    mock_path = mocker.MagicMock(spec=Path)
    mock_client = mocker.MagicMock()

    entity = Entity.load_yaml(mock_path, client=mock_client)

    mock_path.open.assert_called_once_with("r")
    mock_yaml_load.assert_called_once_with(mock_path.open.return_value.__enter__.return_value)
    assert entity.data_dict == {"key": "value"}
    assert isinstance(entity, Entity)


def test_get_item(mock_entity) -> None:
    assert mock_entity["id"] == 1
    assert mock_entity["name"] == "Test Entity"


def test_get_when_present(mock_entity) -> None:
    assert mock_entity.get("id") == 1
    assert mock_entity.get("name") == "Test Entity"


def test_get_when_missing(mock_entity) -> None:
    assert mock_entity.get("missing") is None
    assert mock_entity.get("missing", "default") == "default"


def test_repr(mock_entity, mock_data_dict) -> None:
    entity = Entity(mock_data_dict, None)
    assert repr(entity) == "Entity({'id': 1, 'name': 'Test Entity'}, client=None)"


def test_str(mock_entity, mock_data_dict) -> None:
    entity = Entity(mock_data_dict, None)
    assert str(entity) == "Entity({'id': 1, 'name': 'Test Entity'}, client=None)"


def test_compare_when_possible():
    entity_1 = Entity({"id": 1, "name": "Test Entity"}, None)
    entity_1.ENDPOINT = "X"
    entity_10 = Entity({"id": 10, "name": "Test Entity"}, None)
    entity_10.ENDPOINT = "X"
    assert entity_1 == entity_1
    assert entity_1 < entity_10
    assert entity_10 > entity_1


def test_compare_when_not_possible():
    entity_1 = Entity({"id": 1, "name": "Test Entity"}, None)
    entity_1.ENDPOINT = "X"
    entity_2 = Entity({"id": 2, "name": "Test Entity"}, None)
    entity_2.ENDPOINT = "Y"
    assert entity_1 != entity_2
    with pytest.raises(TypeError):
        _ = entity_1 < entity_2
    with pytest.raises(TypeError):
        _ = entity_1 > entity_2


if __name__ == "__main__":
    pytest.main()

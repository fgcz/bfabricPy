from pathlib import Path

import pytest

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity
from bfabric.entities.core.entity_reader import EntityReader
from bfabric.entities.core.uri import EntityUri


@pytest.fixture
def mock_client(mocker, bfabric_instance):
    config = mocker.Mock(name="mock_client.config")
    config.base_url = bfabric_instance
    return mocker.Mock(spec=Bfabric, config=config)


@pytest.fixture
def mock_data_dict():
    return {"id": 1, "name": "Test Entity", "classname": "testendpoint"}


@pytest.fixture()
def mock_entity(mock_data_dict, mock_client, bfabric_instance) -> Entity:
    return Entity(mock_data_dict, mock_client, bfabric_instance)


@pytest.fixture
def bfabric_instance() -> str:
    return "https://example.com/bfabric/"


def test_classname(mock_entity) -> None:
    assert mock_entity.classname == "testendpoint"


def test_data_dict(mock_entity, mock_data_dict) -> None:
    assert mock_entity.data_dict == mock_data_dict


def test_client(mock_entity, mock_client) -> None:
    assert mock_entity._client == mock_client


def test_find_when_found(mocker, mock_client, bfabric_instance) -> None:
    mocker.patch.object(Entity, "ENDPOINT", new="testendpoint")

    # Mock EntityReader.read_uri to return a GenericEntity
    mock_entity = Entity({"id": 1, "name": "Test Entity", "classname": "testendpoint"}, mock_client, bfabric_instance)
    mock_reader_instance = mocker.MagicMock(spec=EntityReader)
    mock_reader_instance.read_uri.return_value = mock_entity
    mocker.patch.object(EntityReader, "__init__", return_value=None)
    mocker.patch.object(EntityReader, "read_uri", return_value=mock_entity)

    entity = Entity.find(1, mock_client)
    assert isinstance(entity, Entity)
    assert entity.data_dict == {"id": 1, "name": "Test Entity", "classname": "testendpoint"}


def test_find_when_not_found(mocker, mock_client) -> None:
    mocker.patch.object(Entity, "ENDPOINT", new="testendpoint")

    # Mock EntityReader.read_uri to return None
    mocker.patch.object(EntityReader, "__init__", return_value=None)
    mocker.patch.object(EntityReader, "read_uri", return_value=None)

    entity = Entity.find(1, mock_client)
    assert entity is None


def test_find_all_when_all_found(mocker, mock_client, bfabric_instance) -> None:
    mocker.patch.object(Entity, "ENDPOINT", new="testendpoint")

    # Mock EntityReader.read_uris to return an Entity
    uri = EntityUri.from_components(bfabric_instance, "testendpoint", 1)
    mock_entity = Entity({"id": 1, "name": "Test Entity", "classname": "testendpoint"}, mock_client, bfabric_instance)
    mocker.patch.object(EntityReader, "__init__", return_value=None)
    mocker.patch.object(EntityReader, "read_uris", return_value={uri: mock_entity})

    entities = Entity.find_all([1], mock_client)
    assert len(entities) == 1
    assert isinstance(entities[1], Entity)
    assert entities[1].data_dict == {"id": 1, "name": "Test Entity", "classname": "testendpoint"}


def test_find_all_when_not_all_found(mocker, mock_client, bfabric_instance) -> None:
    mocker.patch.object(Entity, "ENDPOINT", new="testendpoint")

    # Mock EntityReader.read_uris to return only one entity (id=5, not id=1)
    uri1 = EntityUri.from_components(bfabric_instance, "testendpoint", 1)
    uri5 = EntityUri.from_components(bfabric_instance, "testendpoint", 5)
    mock_entity = Entity({"id": 5, "name": "Test Entity", "classname": "testendpoint"}, mock_client, bfabric_instance)
    mocker.patch.object(EntityReader, "__init__", return_value=None)
    mocker.patch.object(EntityReader, "read_uris", return_value={uri1: None, uri5: mock_entity})

    entities = Entity.find_all([1, 5], mock_client)
    assert len(entities) == 1
    assert entities[5].data_dict == {"id": 5, "name": "Test Entity", "classname": "testendpoint"}


def test_find_all_when_empty_list(mock_client) -> None:
    entities = Entity.find_all([], mock_client)
    assert entities == {}
    mock_client.read.assert_not_called()
    mock_client.assert_not_called()


def test_find_by_when_found(mocker, mock_client) -> None:
    mock_client.read.return_value = [{"id": 1, "name": "Test Entity", "classname": "testendpoint"}]
    mocker.patch.object(Entity, "ENDPOINT", new="testendpoint")
    entities = Entity.find_by({"id": 1}, mock_client)
    assert len(entities) == 1
    assert isinstance(entities[1], Entity)
    assert entities[1].data_dict == {"id": 1, "name": "Test Entity", "classname": "testendpoint"}
    mock_client.read.assert_called_once_with("testendpoint", obj={"id": 1}, max_results=100)


def test_find_by_when_not_found(mocker, mock_client) -> None:
    mock_client.read.return_value = []
    mocker.patch.object(Entity, "ENDPOINT", new="testendpoint")
    entities = Entity.find_by({"id": 1}, mock_client)
    assert len(entities) == 0
    mock_client.read.assert_called_once_with("testendpoint", obj={"id": 1}, max_results=100)


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

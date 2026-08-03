from pathlib import Path

import pytest

from bfabric.entities.core.entity import Entity


@pytest.fixture
def mock_data_dict():
    return {"id": 1, "name": "Test Entity", "classname": "testendpoint"}


@pytest.fixture()
def mock_entity(mock_data_dict, bfabric_instance) -> Entity:
    return Entity(mock_data_dict, bfabric_instance)


def test_id(mock_entity) -> None:
    assert mock_entity.id == 1


def test_bfabric_instance(mock_entity, bfabric_instance) -> None:
    assert mock_entity.bfabric_instance == bfabric_instance


def test_classname(mock_entity) -> None:
    assert mock_entity.classname == "testendpoint"


def test_uri(mock_entity, bfabric_instance) -> None:
    assert mock_entity.uri == f"{bfabric_instance}testendpoint/show.html?id=1"


def test_data_dict(mock_entity, mock_data_dict) -> None:
    assert mock_entity.data_dict == mock_data_dict


def test_refs(mock_entity, mocker, bfabric_instance) -> None:
    mock_references = mocker.patch("bfabric.entities.core.references.References")
    assert mock_entity.refs == mock_references.return_value
    mock_references.assert_called_once_with(bfabric_instance=bfabric_instance, data_ref=mock_entity.data_dict)


class TestCustomAttributes:
    @pytest.fixture(params=["present", "empty", "missing"])
    def scenario(self, request) -> str:
        return request.param

    @pytest.fixture
    def custom_attributes(self, scenario):
        if scenario == "present":
            return {"attr1": "val1", "attr2": "val2"}
        else:
            return {}

    @pytest.fixture
    def mock_data_dict(self, scenario, mock_data_dict, custom_attributes):
        if scenario in ("present", "empty"):
            mock_data_dict["customattribute"] = [{"name": n, "value": v} for n, v in custom_attributes.items()]
        else:
            assert "customattribute" not in mock_data_dict
        return mock_data_dict

    @pytest.mark.parametrize("scenario", ["present", "empty"], indirect=True)
    def test_custom_attributes(self, mock_entity, custom_attributes):
        assert mock_entity.custom_attributes == custom_attributes

    @pytest.mark.parametrize("scenario", ["missing"], indirect=True)
    def test_custom_attributes_when_missing(self, mock_entity):
        with pytest.raises(AttributeError) as error:
            _ = mock_entity.custom_attributes
        assert str(error.value) == "Entity of classname 'testendpoint' has no custom attributes."


def test_dump_yaml(mocker, mock_entity) -> None:
    mock_yaml_dump = mocker.patch("yaml.safe_dump")
    mock_path = mocker.MagicMock(spec=Path)
    mock_entity.dump_yaml(mock_path)
    mock_path.open.assert_called_once_with("w")
    mock_yaml_dump.assert_called_once_with(mock_entity.data_dict, mock_path.open.return_value.__enter__.return_value)


def test_load_yaml(mocker, bfabric_instance) -> None:
    mock_yaml_load = mocker.patch("yaml.safe_load", return_value={"key": "value"})
    mock_path = mocker.MagicMock(spec=Path)

    entity = Entity.load_yaml(mock_path, bfabric_instance=bfabric_instance)

    mock_path.open.assert_called_once_with("r")
    mock_yaml_load.assert_called_once_with(mock_path.open.return_value.__enter__.return_value)
    assert entity.data_dict == {"key": "value"}
    assert isinstance(entity, Entity)


def test_getitem(mock_entity) -> None:
    assert mock_entity["id"] == 1
    assert mock_entity["name"] == "Test Entity"


def test_contains(mock_entity) -> None:
    assert "id" in mock_entity
    assert "name" in mock_entity
    assert "classname" in mock_entity
    assert "missing" not in mock_entity


def test_get_when_present(mock_entity) -> None:
    assert mock_entity.get("id") == 1
    assert mock_entity.get("name") == "Test Entity"


def test_get_when_missing(mock_entity) -> None:
    assert mock_entity.get("missing") is None
    assert mock_entity.get("missing", "default") == "default"


def test_repr(mock_entity) -> None:
    assert repr(mock_entity) == (
        "Entity("
        "data_dict={'id': 1, 'name': 'Test Entity', 'classname': 'testendpoint'}, "
        "bfabric_instance='https://bfabric.example.org/bfabric/'"
        ")"
    )


def test_str(mock_entity) -> None:
    assert str(mock_entity) == repr(mock_entity)


def test_compare_when_possible():
    entity_1 = Entity({"classname": "test", "id": 1, "name": "Test Entity"}, None)
    entity_1.ENDPOINT = "X"
    entity_10 = Entity({"classname": "test", "id": 10, "name": "Test Entity"}, None)
    entity_10.ENDPOINT = "X"
    assert entity_1 == entity_1
    assert entity_1 < entity_10
    assert entity_10 > entity_1


def test_compare_when_not_possible():
    entity_1 = Entity({"classname": "test", "id": 1, "name": "Test Entity"}, None)
    entity_1.ENDPOINT = "X"
    entity_2 = Entity({"classname": "resource", "id": 2, "name": "Test Entity"}, None)
    entity_2.ENDPOINT = "Y"
    assert entity_1 != entity_2
    with pytest.raises(TypeError):
        _ = entity_1 < entity_2
    with pytest.raises(TypeError):
        _ = entity_1 > entity_2


if __name__ == "__main__":
    pytest.main()

import pytest

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity
from bfabric.entities.core.uri import EntityUri
from bfabric.experimental.update_custom_attributes import update_custom_attributes


@pytest.fixture
def client(mocker):
    return mocker.MagicMock(name="client", spec=Bfabric)


@pytest.fixture
def entity_uri(bfabric_instance):
    return EntityUri.from_components(bfabric_instance, "mockentity", 1234)


@pytest.fixture
def existing_entity(client, bfabric_instance):
    data_dict = {"classname": "mockentity", "id": 1234, "customattribute": [{"name": "species", "value": "quokka"}]}
    return Entity(data_dict, client=client, bfabric_instance=bfabric_instance)


def test_update_merge(client, entity_uri, existing_entity):
    client.reader.read_uri.return_value = existing_entity
    update_custom_attributes(client=client, entity_uri=entity_uri, custom_attributes={"wikidata": "Q726151"})
    client.save.assert_called_once_with(
        "mockentity",
        {
            "id": 1234,
            "customattribute": [{"name": "species", "value": "quokka"}, {"name": "wikidata", "value": "Q726151"}],
        },
    )
    client.reader.read_uri.assert_called_once_with(entity_uri)


def test_update_replace(client, entity_uri, existing_entity):
    update_custom_attributes(
        client=client, entity_uri=entity_uri, custom_attributes={"wikidata": "Q726151"}, replace=True
    )
    client.save.assert_called_once_with(
        "mockentity", {"id": 1234, "customattribute": [{"name": "wikidata", "value": "Q726151"}]}
    )
    client.reader.read_uri.assert_not_called()

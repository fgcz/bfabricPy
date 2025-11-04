import pytest

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity
from bfabric.entities.core.references import References


@pytest.fixture
def bfabric_instance():
    return "https://example.com/bfabric/"


@pytest.fixture
def entity_data_dict():
    return {
        "id": 42,
        "classname": "order",
        "name": "Test Order",
        "container": {"id": 3000, "classname": "project"},
        "member": [
            {
                "id": 1,
                "classname": "user",
                "name": "Test User",
                "email": "test@example.com",
            }
        ],
    }


@pytest.fixture
def client(mocker, bfabric_instance):
    config = mocker.MagicMock(name="client.config", base_url=bfabric_instance)
    return mocker.MagicMock(name="client", spec=Bfabric, config=config)


@pytest.fixture
def entity(entity_data_dict, client, bfabric_instance):
    return Entity(data_dict=entity_data_dict, client=client, bfabric_instance=bfabric_instance)


@pytest.fixture
def entity_reader_constructor(mocker):
    return mocker.patch(
        "bfabric.entities.core.entity_reader.EntityReader",
        autospec=True,
    )


@pytest.fixture
def entity_reader(mocker, entity_reader_constructor):
    reader_instance = mocker.MagicMock(name="entity_reader")
    entity_reader_constructor.return_value = reader_instance
    return reader_instance


@pytest.fixture
def mock_project(mocker, bfabric_instance):
    mock_project = mocker.MagicMock(name="mock_entity")
    mock_project.uri = f"{bfabric_instance}project/show.html?id=3000"
    mock_project.data_dict = {"id": 3000, "classname": "project", "name": "Mock Project"}
    return mock_project


@pytest.fixture
def refs(client, entity_data_dict):
    return References(client=client, data_ref=entity_data_dict)


def test_uris(refs):
    assert refs.uris == {
        "container": "https://example.com/bfabric/project/show.html?id=3000",
        "member": ["https://example.com/bfabric/user/show.html?id=1"],
    }


class TestIsLoaded:
    def test_loaded(self, refs):
        assert refs.is_loaded("member") == True

    def test_not_loaded(self, refs):
        assert refs.is_loaded("container") == False

    def test_not_exists(self, refs):
        with pytest.raises(KeyError):
            refs.is_loaded("nonexistent")


def test_contains(refs):
    assert "container" in refs
    assert "member" in refs
    assert "nonexistent" not in refs


class TestGet:
    def test_loaded(self, refs):
        assert refs.is_loaded("member") == True
        members = refs.get("member")
        assert len(members) == 1
        assert members[0].data_dict == {
            "id": 1,
            "classname": "user",
            "name": "Test User",
            "email": "test@example.com",
        }
        assert refs.is_loaded("member") == True

    def test_not_loaded(self, refs, mock_project, entity_reader):
        assert refs.is_loaded("container") == False
        entity_reader.read_uris.return_value = {mock_project.uri: mock_project}
        container = refs.get("container")
        assert refs.is_loaded("container") == True
        assert container.data_dict == mock_project.data_dict

    def test_not_exists(self, refs):
        value = refs.get("nonexistent")
        assert value is None

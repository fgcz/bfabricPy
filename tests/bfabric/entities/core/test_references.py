import pytest

from bfabric.entities import User, Project
from bfabric.entities.core.entity import Entity
from bfabric.entities.core.entity_reader import EntityReader
from bfabric.entities.core.references import References


@pytest.fixture(params=[True, False])
def refs_loaded(request) -> bool:
    if hasattr(request, "param"):
        return request.param
    return True


@pytest.fixture
def entity_data_dict(refs_loaded):
    container = {"id": 3000, "classname": "project"}
    member = {"id": 1, "classname": "user"}
    if refs_loaded:
        container["name"] = "Test Project"
        member["name"] = "Test User"
        member["email"] = "test@bfabric.example.org"

    return {
        "id": 42,
        "classname": "order",
        "name": "Test Order",
        "container": container,
        "member": [member],
        "technologies": ["proteomics", "genomics"],
    }


@pytest.fixture
def entity(entity_data_dict, mock_client, bfabric_instance):
    return Entity(data_dict=entity_data_dict, client=mock_client, bfabric_instance=bfabric_instance)


@pytest.fixture
def entity_reader_constructor(mocker):
    return mocker.patch.object(EntityReader, "for_client", autospec=True)


@pytest.fixture
def entity_reader(mocker, entity_reader_constructor):
    reader_instance = mocker.MagicMock(name="entity_reader")
    entity_reader_constructor.return_value = reader_instance
    return reader_instance


@pytest.fixture
def mock_project(mocker, bfabric_instance):
    project = mocker.MagicMock(name="mock_project")
    project.uri = f"{bfabric_instance}project/show.html?id=3000"
    project.data_dict = {"id": 3000, "classname": "project", "name": "Mock Project"}
    return project


@pytest.fixture
def mock_user(mocker, bfabric_instance):
    user = mocker.MagicMock(name="mock_user")
    user.uri = f"{bfabric_instance}user/show.html?id=1"
    user.data_dict = {"id": 1, "classname": "user", "name": "Test User", "email": "test@bfabric.example.org"}
    return user


@pytest.fixture
def refs(mock_client, entity_data_dict, bfabric_instance):
    return References(client=mock_client, data_ref=entity_data_dict, bfabric_instance=bfabric_instance)


def test_uris(refs):
    assert refs.uris == {
        "container": "https://bfabric.example.org/bfabric/project/show.html?id=3000",
        "member": ["https://bfabric.example.org/bfabric/user/show.html?id=1"],
    }


class TestIsLoaded:
    def test_loaded(self, refs, refs_loaded):
        assert refs.is_loaded("member") == refs_loaded
        assert refs.is_loaded("container") == refs_loaded

    def test_not_exists(self, refs):
        with pytest.raises(KeyError):
            refs.is_loaded("nonexistent")


def test_contains(refs):
    assert "container" in refs
    assert "member" in refs
    assert "nonexistent" not in refs


class TestGet:
    @pytest.mark.parametrize("refs_loaded", [True], indirect=True)
    def test_loaded_singular(self, refs):
        assert refs.is_loaded("container") == True
        container = refs.get("container")
        assert container.data_dict == {
            "id": 3000,
            "classname": "project",
            "name": "Test Project",
        }

    @pytest.mark.parametrize("refs_loaded", [True], indirect=True)
    def test_loaded_multiple(self, refs):
        assert refs.is_loaded("member") == True
        members = refs.get("member")
        assert len(members) == 1
        assert members[0].data_dict == {
            "id": 1,
            "classname": "user",
            "name": "Test User",
            "email": "test@bfabric.example.org",
        }
        assert isinstance(members[0], User)
        assert refs.is_loaded("member") == True

    def test_caching(self, refs, mock_user, mock_project, entity_reader):
        # NOTE: There is some overlap with the remaining tests
        entity_reader.read_uris.return_value = {mock_project.uri: mock_project, mock_user.uri: mock_user}
        assert refs.get("member") is refs.get("member")
        assert refs.get("container") is refs.get("container")

    @pytest.mark.parametrize("refs_loaded", [False], indirect=True)
    def test_not_loaded_singular(self, refs, mock_project, entity_reader):
        assert refs.is_loaded("container") == False
        entity_reader.read_uris.return_value = {mock_project.uri: mock_project}
        container = refs.get("container")
        assert refs.is_loaded("container") == True
        assert isinstance(container, Project)
        assert container.data_dict == mock_project.data_dict

    @pytest.mark.parametrize("refs_loaded", [False], indirect=True)
    def test_not_loaded_multiple(self, refs, mock_user, entity_reader):
        assert refs.is_loaded("member") == False
        entity_reader.read_uris.return_value = {mock_user.uri: mock_user}
        members = refs.get("member")
        assert len(members) == 1
        assert refs.is_loaded("member") == True
        assert isinstance(members[0], User)
        assert members[0].data_dict == mock_user.data_dict

    def test_not_exists(self, refs):
        value = refs.get("nonexistent")
        assert value is None


class TestGetAttr:
    def test_when_present(self, mocker, refs):
        entity = mocker.MagicMock(name="entity")
        mocker.patch.object(refs, "get").return_value = entity
        assert refs.container == entity
        assert refs.member == entity

    def test_when_missing(self, mocker, refs):
        mocker.patch.object(refs, "get").return_value = None
        with pytest.raises(AttributeError) as error:
            _ = refs.container
        assert str(error.value) == "'References' object has no attribute 'container'"

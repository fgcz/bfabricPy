import pytest

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.entity_reader import EntityReader
from bfabric.entities.core.uri import EntityUri


@pytest.fixture
def entity_reader(mock_client):
    return EntityReader(client=mock_client)


@pytest.fixture
def mock_cache_stack(mocker):
    """Mock the cache stack returned by get_cache_stack()."""
    mock_stack = mocker.MagicMock(name="mock_cache_stack")
    mocker.patch("bfabric.entities.core.entity_reader.get_cache_stack", return_value=mock_stack)
    return mock_stack


@pytest.fixture
def mock_multi_query(mocker):
    """Mock the MultiQuery class."""
    mock_mq_class = mocker.patch("bfabric.entities.core.entity_reader.MultiQuery")
    mock_instance = mocker.MagicMock(name="mock_multi_query_instance")
    mock_mq_class.return_value = mock_instance
    return mock_instance


@pytest.fixture
def mock_instantiate_entity(mocker):
    """Mock the instantiate_entity function."""
    return mocker.patch("bfabric.entities.core.entity_reader.instantiate_entity")


@pytest.fixture
def uri_project_1(bfabric_instance):
    return EntityUri(f"{bfabric_instance}project/show.html?id=100")


@pytest.fixture
def uri_project_2(bfabric_instance):
    return EntityUri(f"{bfabric_instance}project/show.html?id=200")


@pytest.fixture
def uri_user_1(bfabric_instance):
    return EntityUri(f"{bfabric_instance}user/show.html?id=1")


@pytest.fixture
def uri_user_2(bfabric_instance):
    return EntityUri(f"{bfabric_instance}user/show.html?id=2")


@pytest.fixture
def uri_wrong_instance():
    return EntityUri("https://other-instance.example.org/bfabric/project/show.html?id=100")


@pytest.fixture
def mock_entity_project_1(mocker, uri_project_1, bfabric_instance):
    entity = mocker.MagicMock(name="mock_entity_project_1", spec=Entity)
    entity.uri = uri_project_1
    entity.data_dict = {"id": 100, "classname": "project", "name": "Project 1"}
    return entity


@pytest.fixture
def mock_entity_project_2(mocker, uri_project_2, bfabric_instance):
    entity = mocker.MagicMock(name="mock_entity_project_2", spec=Entity)
    entity.uri = uri_project_2
    entity.data_dict = {"id": 200, "classname": "project", "name": "Project 2"}
    return entity


@pytest.fixture
def mock_entity_user_1(mocker, uri_user_1, bfabric_instance):
    entity = mocker.MagicMock(name="mock_entity_user_1", spec=Entity)
    entity.uri = uri_user_1
    entity.data_dict = {"id": 1, "classname": "user", "name": "User 1"}
    return entity


@pytest.fixture
def mock_entity_user_2(mocker, uri_user_2, bfabric_instance):
    entity = mocker.MagicMock(name="mock_entity_user_2", spec=Entity)
    entity.uri = uri_user_2
    entity.data_dict = {"id": 2, "classname": "user", "name": "User 2"}
    return entity


class TestReadUri:
    def test_read_single_uri(
        self,
        entity_reader,
        mock_cache_stack,
        uri_project_1,
        mock_entity_project_1,
        mock_multi_query,
        mock_instantiate_entity,
    ):
        """Test that read_uri delegates to read_uris and returns a single entity."""
        mock_cache_stack.item_get_all.return_value = {}
        mock_multi_query.read_multi.return_value = [{"id": 100, "classname": "project", "name": "Project 1"}]
        mock_instantiate_entity.return_value = mock_entity_project_1

        result = entity_reader.read_uri(uri_project_1)

        assert result == mock_entity_project_1
        mock_cache_stack.item_get_all.assert_called()


class TestReadUris:
    def test_all_cached(
        self, entity_reader, mock_cache_stack, uri_project_1, uri_user_1, mock_entity_project_1, mock_entity_user_1
    ):
        """Test when all entities are found in cache."""
        mock_cache_stack.item_get_all.return_value = {
            uri_project_1: mock_entity_project_1,
            uri_user_1: mock_entity_user_1,
        }

        result = entity_reader.read_uris([uri_project_1, uri_user_1])

        assert result == {uri_project_1: mock_entity_project_1, uri_user_1: mock_entity_user_1}
        mock_cache_stack.item_get_all.assert_called()
        mock_cache_stack.item_put_all.assert_not_called()  # No fresh results to cache

    def test_all_from_api(
        self,
        entity_reader,
        mock_cache_stack,
        mock_multi_query,
        mock_instantiate_entity,
        uri_project_1,
        uri_project_2,
        mock_entity_project_1,
        mock_entity_project_2,
        bfabric_instance,
    ):
        """Test when no entities are in cache and must be fetched."""
        mock_cache_stack.item_get_all.return_value = {}
        mock_multi_query.read_multi.return_value = [
            {"id": 100, "classname": "project", "name": "Project 1"},
            {"id": 200, "classname": "project", "name": "Project 2"},
        ]
        mock_instantiate_entity.side_effect = [mock_entity_project_1, mock_entity_project_2]

        result = entity_reader.read_uris([uri_project_1, uri_project_2])

        assert result == {uri_project_1: mock_entity_project_1, uri_project_2: mock_entity_project_2}
        mock_multi_query.read_multi.assert_called_once_with(
            endpoint="project", obj={}, multi_query_key="id", multi_query_vals=[100, 200]
        )
        mock_cache_stack.item_put_all.assert_called()
        assert mock_instantiate_entity.call_count == 2

    def test_mixed_cached_and_api(
        self,
        entity_reader,
        mock_cache_stack,
        mock_multi_query,
        mock_instantiate_entity,
        uri_project_1,
        uri_project_2,
        mock_entity_project_1,
        mock_entity_project_2,
    ):
        """Test when some entities are cached and others need to be fetched."""
        mock_cache_stack.item_get_all.return_value = {uri_project_1: mock_entity_project_1}
        mock_multi_query.read_multi.return_value = [{"id": 200, "classname": "project", "name": "Project 2"}]
        mock_instantiate_entity.return_value = mock_entity_project_2

        result = entity_reader.read_uris([uri_project_1, uri_project_2])

        assert result == {uri_project_1: mock_entity_project_1, uri_project_2: mock_entity_project_2}
        mock_multi_query.read_multi.assert_called_once_with(
            endpoint="project", obj={}, multi_query_key="id", multi_query_vals=[200]
        )

    def test_multiple_entity_types(
        self,
        entity_reader,
        mock_cache_stack,
        mock_multi_query,
        mock_instantiate_entity,
        uri_project_1,
        uri_user_1,
        mock_entity_project_1,
        mock_entity_user_1,
    ):
        """Test reading URIs of different entity types in a single call."""
        mock_cache_stack.item_get_all.return_value = {}

        def multi_query_side_effect(endpoint, obj, multi_query_key, multi_query_vals):
            if endpoint == "project":
                return [{"id": 100, "classname": "project", "name": "Project 1"}]
            elif endpoint == "user":
                return [{"id": 1, "classname": "user", "name": "User 1"}]
            return []

        mock_multi_query.read_multi.side_effect = multi_query_side_effect
        mock_instantiate_entity.side_effect = [mock_entity_project_1, mock_entity_user_1]

        result = entity_reader.read_uris([uri_project_1, uri_user_1])

        assert result == {uri_project_1: mock_entity_project_1, uri_user_1: mock_entity_user_1}
        assert mock_multi_query.read_multi.call_count == 2

    def test_empty_uri_list(self, entity_reader, mock_cache_stack):
        """Test reading an empty list of URIs."""
        mock_cache_stack.item_get_all.return_value = {}

        result = entity_reader.read_uris([])

        assert result == {}

    def test_missing_entity_returns_none(
        self,
        entity_reader,
        mock_cache_stack,
        mock_multi_query,
        uri_project_1,
        uri_project_2,
        mock_entity_project_1,
        mock_instantiate_entity,
    ):
        """Test that missing entities (not found in API) are returned as None."""
        mock_cache_stack.item_get_all.return_value = {}
        # API only returns project 1, not project 2
        mock_multi_query.read_multi.return_value = [{"id": 100, "classname": "project", "name": "Project 1"}]
        mock_instantiate_entity.return_value = mock_entity_project_1

        result = entity_reader.read_uris([uri_project_1, uri_project_2])

        assert result == {uri_project_1: mock_entity_project_1, uri_project_2: None}

    def test_accepts_string_uris(
        self,
        entity_reader,
        mock_cache_stack,
        mock_multi_query,
        mock_instantiate_entity,
        uri_project_1,
        mock_entity_project_1,
    ):
        """Test that string URIs are converted to EntityUri objects."""
        mock_cache_stack.item_get_all.return_value = {}
        mock_multi_query.read_multi.return_value = [{"id": 100, "classname": "project", "name": "Project 1"}]
        mock_instantiate_entity.return_value = mock_entity_project_1

        result = entity_reader.read_uris([str(uri_project_1)])

        assert uri_project_1 in result


class TestReadByEntityId:
    def test_read_single_entity(
        self,
        entity_reader,
        mock_cache_stack,
        mock_multi_query,
        mock_instantiate_entity,
        mock_entity_project_1,
        bfabric_instance,
    ):
        """Test reading a single entity by ID."""
        mock_cache_stack.item_get_all.return_value = {}
        mock_multi_query.read_multi.return_value = [{"id": 100, "classname": "project", "name": "Project 1"}]
        mock_instantiate_entity.return_value = mock_entity_project_1

        result = entity_reader.read_by_entity_id(entity_type="project", entity_id=100)

        assert result == mock_entity_project_1
        mock_multi_query.read_multi.assert_called_once_with(
            endpoint="project", obj={}, multi_query_key="id", multi_query_vals=[100]
        )

    def test_read_missing_entity_returns_none(
        self, entity_reader, mock_cache_stack, mock_multi_query, bfabric_instance
    ):
        """Test that reading a non-existent entity returns None."""
        mock_cache_stack.item_get_all.return_value = {}
        mock_multi_query.read_multi.return_value = []

        result = entity_reader.read_by_entity_id(entity_type="project", entity_id=999)

        assert result is None

    def test_with_custom_bfabric_instance(
        self,
        entity_reader,
        mock_cache_stack,
        mock_multi_query,
        mock_instantiate_entity,
        mock_entity_project_1,
    ):
        """Test reading with a custom bfabric_instance."""
        custom_instance = "https://bfabric.example.org/bfabric/"
        mock_cache_stack.item_get_all.return_value = {}
        mock_multi_query.read_multi.return_value = [{"id": 100, "classname": "project", "name": "Project 1"}]
        mock_instantiate_entity.return_value = mock_entity_project_1

        result = entity_reader.read_by_entity_id(entity_type="project", entity_id=100, bfabric_instance=custom_instance)

        assert result == mock_entity_project_1


class TestReadByEntityIds:
    def test_read_multiple_entities(
        self,
        entity_reader,
        mock_cache_stack,
        mock_multi_query,
        mock_instantiate_entity,
        uri_project_1,
        uri_project_2,
        mock_entity_project_1,
        mock_entity_project_2,
        bfabric_instance,
    ):
        """Test reading multiple entities by IDs."""
        mock_cache_stack.item_get_all.return_value = {}
        mock_multi_query.read_multi.return_value = [
            {"id": 100, "classname": "project", "name": "Project 1"},
            {"id": 200, "classname": "project", "name": "Project 2"},
        ]
        mock_instantiate_entity.side_effect = [mock_entity_project_1, mock_entity_project_2]

        result = entity_reader.read_by_entity_ids(entity_type="project", entity_ids=[100, 200])

        assert result == {uri_project_1: mock_entity_project_1, uri_project_2: mock_entity_project_2}
        mock_multi_query.read_multi.assert_called_once_with(
            endpoint="project", obj={}, multi_query_key="id", multi_query_vals=[100, 200]
        )

    def test_some_missing_entities(
        self,
        entity_reader,
        mock_cache_stack,
        mock_multi_query,
        mock_instantiate_entity,
        uri_project_1,
        mock_entity_project_1,
        bfabric_instance,
    ):
        """Test reading when some entities don't exist."""
        mock_cache_stack.item_get_all.return_value = {}
        mock_multi_query.read_multi.return_value = [{"id": 100, "classname": "project", "name": "Project 1"}]
        mock_instantiate_entity.return_value = mock_entity_project_1

        result = entity_reader.read_by_entity_ids(entity_type="project", entity_ids=[100, 999])

        expected_uri_999 = EntityUri(f"{bfabric_instance}project/show.html?id=999")
        assert result == {uri_project_1: mock_entity_project_1, expected_uri_999: None}

    def test_all_missing_entities(self, entity_reader, mock_cache_stack, mock_multi_query, bfabric_instance):
        """Test reading when all entities don't exist."""
        mock_cache_stack.item_get_all.return_value = {}
        mock_multi_query.read_multi.return_value = []

        result = entity_reader.read_by_entity_ids(entity_type="project", entity_ids=[999, 888])

        expected_uri_999 = EntityUri(f"{bfabric_instance}project/show.html?id=999")
        expected_uri_888 = EntityUri(f"{bfabric_instance}project/show.html?id=888")
        assert result == {expected_uri_999: None, expected_uri_888: None}

    def test_empty_list(self, entity_reader, mock_cache_stack):
        """Test reading an empty list of entity IDs."""
        mock_cache_stack.item_get_all.return_value = {}

        result = entity_reader.read_by_entity_ids(entity_type="project", entity_ids=[])

        assert result == {}

    def test_with_custom_bfabric_instance(
        self,
        entity_reader,
        mock_cache_stack,
        mock_multi_query,
        mock_instantiate_entity,
        mock_entity_project_1,
        bfabric_instance,
    ):
        """Test reading with a custom bfabric_instance."""
        custom_instance = "https://bfabric.example.org/bfabric/"
        mock_cache_stack.item_get_all.return_value = {}
        mock_multi_query.read_multi.return_value = [{"id": 100, "classname": "project", "name": "Project 1"}]
        mock_instantiate_entity.return_value = mock_entity_project_1

        result = entity_reader.read_by_entity_ids(
            entity_type="project", entity_ids=[100], bfabric_instance=custom_instance
        )

        # Verify URI was constructed with custom instance
        expected_uri = EntityUri(f"{custom_instance}project/show.html?id=100")
        assert expected_uri in result


class TestQueryBy:
    def test_successful_query(
        self, entity_reader, mock_cache_stack, mock_client, bfabric_instance, mock_instantiate_entity
    ):
        """Test successful query_by with results."""
        mock_cache_stack.item_get_all.return_value = {}
        mock_client.read.return_value = [
            {"id": 100, "classname": "project", "name": "Project 1"},
            {"id": 200, "classname": "project", "name": "Project 2"},
        ]

        mock_entity_1 = Entity(
            data_dict={"id": 100, "classname": "project", "name": "Project 1"},
            client=mock_client,
            bfabric_instance=bfabric_instance,
        )
        mock_entity_2 = Entity(
            data_dict={"id": 200, "classname": "project", "name": "Project 2"},
            client=mock_client,
            bfabric_instance=bfabric_instance,
        )
        mock_instantiate_entity.side_effect = [mock_entity_1, mock_entity_2]

        result = entity_reader.query_by(
            entity_type="project", obj={"name": "Project"}, bfabric_instance=bfabric_instance, max_results=10
        )

        assert len(result) == 2
        assert mock_entity_1.uri in result
        assert mock_entity_2.uri in result
        mock_client.read.assert_called_once_with("project", obj={"name": "Project"}, max_results=10)
        mock_cache_stack.item_put_all.assert_called_once()

    def test_empty_results(self, entity_reader, mock_cache_stack, mock_client, bfabric_instance):
        """Test query_by with no results."""
        mock_cache_stack.item_get_all.return_value = {}
        mock_client.read.return_value = []

        result = entity_reader.query_by(
            entity_type="project", obj={"name": "Nonexistent"}, bfabric_instance=bfabric_instance
        )

        assert result == {}

    def test_instance_mismatch_raises_error(self, entity_reader, mock_client, bfabric_instance):
        """Test that querying a different instance raises ValueError."""
        different_instance = "https://other-instance.example.org/bfabric/"

        with pytest.raises(ValueError) as exc_info:
            entity_reader.query_by(entity_type="project", obj={}, bfabric_instance=different_instance, max_results=100)

        assert f"Unsupported B-Fabric instance: {different_instance}" in str(exc_info.value)


class TestGroupByEntityType:
    def test_single_entity_type(self, uri_project_1, uri_project_2):
        """Test grouping URIs of a single entity type."""
        result = EntityReader._group_by_entity_type([uri_project_1, uri_project_2])

        assert result == {"project": [uri_project_1, uri_project_2]}

    def test_multiple_entity_types(self, uri_project_1, uri_project_2, uri_user_1, uri_user_2):
        """Test grouping URIs of multiple entity types."""
        result = EntityReader._group_by_entity_type([uri_project_1, uri_user_1, uri_project_2, uri_user_2])

        assert result == {
            "project": [uri_project_1, uri_project_2],
            "user": [uri_user_1, uri_user_2],
        }

    def test_empty_list(self):
        """Test grouping an empty list."""
        result = EntityReader._group_by_entity_type([])

        assert result == {}


class TestValidateUris:
    def test_valid_uris(self, entity_reader, uri_project_1, uri_user_1):
        """Test that valid URIs pass validation."""
        # Should not raise
        entity_reader._validate_uris([uri_project_1, uri_user_1])

    def test_unsupported_instance_raises_error(self, entity_reader, uri_project_1, uri_wrong_instance):
        """Test that URIs from unsupported instances raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            entity_reader._validate_uris([uri_project_1, uri_wrong_instance])

        assert "Unsupported B-Fabric instances" in str(exc_info.value)
        assert "https://other-instance.example.org/bfabric/" in str(exc_info.value)

    def test_all_wrong_instances_raises_error(self, entity_reader, uri_wrong_instance):
        """Test that all wrong instances raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            entity_reader._validate_uris([uri_wrong_instance])

        assert "Unsupported B-Fabric instances" in str(exc_info.value)


class TestRetrieveEntities:
    def test_retrieve_entities(
        self,
        entity_reader,
        mock_multi_query,
        mock_instantiate_entity,
        uri_project_1,
        uri_project_2,
        mock_entity_project_1,
        mock_entity_project_2,
    ):
        """Test retrieving entities from the API."""
        mock_multi_query.read_multi.return_value = [
            {"id": 100, "classname": "project", "name": "Project 1"},
            {"id": 200, "classname": "project", "name": "Project 2"},
        ]
        mock_instantiate_entity.side_effect = [mock_entity_project_1, mock_entity_project_2]

        result = entity_reader._retrieve_entities([uri_project_1, uri_project_2])

        assert result == {uri_project_1: mock_entity_project_1, uri_project_2: mock_entity_project_2}
        mock_multi_query.read_multi.assert_called_once()

    def test_empty_list_returns_empty(self, entity_reader):
        """Test that an empty list returns an empty dict without making API calls."""
        result = entity_reader._retrieve_entities([])

        assert result == {}

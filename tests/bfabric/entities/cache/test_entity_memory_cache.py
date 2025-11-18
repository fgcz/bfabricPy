import pytest

from bfabric.entities.core.uri import EntityUri
from bfabric.entities.cache._entity_memory_cache import EntityMemoryCache


@pytest.fixture
def config():
    return {"project": 3, "sample": 2}


@pytest.fixture
def mock_entity1(mocker):
    return mocker.Mock(uri=EntityUri("https://bfabric.example.com/bfabric/project/show.html?id=1"), id=1)


@pytest.fixture
def mock_entity2(mocker):
    return mocker.Mock(uri=EntityUri("https://bfabric.example.com/bfabric/project/show.html?id=2"), id=2)


@pytest.fixture
def mock_entity3(mocker):
    return mocker.Mock(uri=EntityUri("https://bfabric.example.com/bfabric/project/show.html?id=3"), id=3)


@pytest.fixture
def mock_entity4(mocker):
    return mocker.Mock(uri=EntityUri("https://bfabric.example.com/bfabric/project/show.html?id=4"), id=4)


@pytest.fixture()
def entity_cache(config, mock_entity1, mock_entity2):
    result = EntityMemoryCache(config)
    result.put(mock_entity1)
    result.put(mock_entity2)
    return result


def test_entity_lookup_cache_contains(entity_cache, mock_entity1, mock_entity2, mock_entity3):
    assert entity_cache.contains(mock_entity1.uri)
    assert entity_cache.contains(mock_entity2.uri)
    assert not entity_cache.contains(mock_entity3.uri)

    # Test sample type which is in config but empty
    uri_sample = EntityUri("https://bfabric.example.com/bfabric/sample/show.html?id=1")
    assert not entity_cache.contains(uri_sample)


def test_entity_lookup_cache_get_when_exists(entity_cache, mock_entity1, mock_entity2):
    assert entity_cache.get(mock_entity1.uri) == mock_entity1
    assert entity_cache.get(mock_entity2.uri) == mock_entity2


def test_entity_lookup_cache_get_when_not_exists(entity_cache, mock_entity3):
    assert entity_cache.get(mock_entity3.uri) is None


def test_entity_lookup_cache_get_all(entity_cache, mock_entity1, mock_entity2, mock_entity3):
    result = entity_cache.get_all([mock_entity1.uri, mock_entity2.uri, mock_entity3.uri])
    assert result == {mock_entity1.uri: mock_entity1, mock_entity2.uri: mock_entity2}


def test_entity_lookup_cache_put(entity_cache, mock_entity1, mock_entity2, mock_entity3, mock_entity4):
    entity_cache.put(mock_entity3)
    entity_cache.put(mock_entity4)
    # Cache size is 3, so entity1 should be evicted (FIFO)
    assert entity_cache.get(mock_entity1.uri) is None
    assert entity_cache.get(mock_entity2.uri) == mock_entity2
    assert entity_cache.get(mock_entity3.uri) == mock_entity3
    assert entity_cache.get(mock_entity4.uri) == mock_entity4


def test_entity_lookup_cache_put_when_type_not_in_config(entity_cache, mocker):
    entity_workunit = mocker.Mock(uri=EntityUri("https://bfabric.example.com/bfabric/workunit/show.html?id=1"), id=1)
    entity_cache.put(entity_workunit)
    assert entity_cache.get(entity_workunit.uri) is None

import pytest

from bfabric.experimental.cache._entity_memory_cache import EntityMemoryCache


@pytest.fixture
def config():
    return {
        "Entity1": 3,
        "Entity2": 2,
    }


@pytest.fixture()
def entity_cache(config):
    result = EntityMemoryCache(config)
    result.put("Entity1", 1, "value1")
    result.put("Entity1", 2, "value2")
    return result


def test_entity_lookup_cache_contains(entity_cache):
    assert entity_cache.contains("Entity1", 1)
    assert entity_cache.contains("Entity1", 2)
    assert not entity_cache.contains("Entity1", 3)
    assert not entity_cache.contains("Entity2", 1)


def test_entity_lookup_cache_get_when_exists(entity_cache):
    assert entity_cache.get("Entity1", 1) == "value1"
    assert entity_cache.get("Entity1", 2) == "value2"


def test_entity_lookup_cache_get_when_not_exists(entity_cache):
    assert entity_cache.get("Entity1", 3) is None


def test_entity_lookup_cache_get_all(entity_cache):
    result = entity_cache.get_all("Entity1", [1, 2, 3])
    assert result == {1: "value1", 2: "value2"}


def test_entity_lookup_cache_put(entity_cache):
    entity_cache.put("Entity1", 3, "value3")
    entity_cache.put("Entity1", 4, "value4")
    assert entity_cache.get("Entity1", 1) is None
    assert entity_cache.get("Entity1", 2) == "value2"
    assert entity_cache.get("Entity1", 3) == "value3"
    assert entity_cache.get("Entity1", 4) == "value4"


def test_entity_lookup_cache_put_when_type_not_in_config(entity_cache):
    entity_cache.put("Entity3", 1, "value1")
    assert entity_cache.get("Entity3", 1) is None

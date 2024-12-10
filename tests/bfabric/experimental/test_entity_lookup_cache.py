import pytest

from bfabric.experimental.entity_lookup_cache import Cache, EntityLookupCache


@pytest.fixture()
def max_size() -> int:
    return 3


@pytest.fixture()
def cache(max_size: int):
    cache = Cache(max_size=max_size)
    cache.put("key1", "value1")
    cache.put("key2", "value2")
    return cache


@pytest.fixture()
def entity_cache(max_size: int):
    result = EntityLookupCache(max_size=max_size)
    result.put("Entity1", 1, "value1")
    result.put("Entity1", 2, "value2")
    return result


def test_cache_get_when_exists(cache):
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"


def test_cache_get_when_not_exists(cache):
    assert cache.get("missing") is None


@pytest.mark.parametrize("max_size", [0, 3])
def test_cache_put(cache, max_size):
    cache.put("key3", "value3")
    cache.put("key4", "value4")
    if max_size == 3:
        assert cache.get("key1") is None
    else:
        assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"
    assert cache.get("key3") == "value3"
    assert cache.get("key4") == "value4"


def test_cache_contains(cache):
    assert "key1" in cache
    assert "key2" in cache
    assert "key3" not in cache


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


def test_entity_lookup_cache_enable(entity_cache):
    assert entity_cache.instance() is None
    with entity_cache.enable():
        first_instance = entity_cache.instance()
        assert first_instance is not None
        with entity_cache.enable():
            second_instance = entity_cache.instance()
            assert first_instance is second_instance
        assert entity_cache.instance() is first_instance
    assert entity_cache.instance() is None

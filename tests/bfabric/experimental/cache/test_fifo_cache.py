import pytest

from bfabric.experimental.cache._fifo_cache import FifoCache


@pytest.fixture()
def max_size() -> int:
    return 3


@pytest.fixture()
def cache(max_size: int):
    cache = FifoCache(max_size=max_size)
    cache.put("key1", "value1")
    cache.put("key2", "value2")
    return cache


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


def test_cache_put_when_key_exists(cache):
    cache.put("key1", "new_value1")
    assert cache.get("key1") == "new_value1"
    assert cache.get("key2") == "value2"


def test_cache_contains(cache):
    assert "key1" in cache
    assert "key2" in cache
    assert "key3" not in cache

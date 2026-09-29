from __future__ import annotations

import json
import stat

import pytest

from bfabric.transfer.hash_cache import HashCache


@pytest.fixture
def cache_path(tmp_path):
    return tmp_path / "hashes.json"


@pytest.fixture
def sample(tmp_path):
    path = tmp_path / "a.raw"
    path.write_bytes(b"abc")
    return path


class TestHashCache:
    def test_flushed_entry_is_found_by_a_new_instance(self, cache_path, sample):
        cache = HashCache(cache_path)
        cache.put(sample, size=3, mtime_ns=7, md5="m")
        cache.flush()
        assert HashCache(cache_path).get(sample, size=3, mtime_ns=7) == "m"

    def test_entry_is_visible_before_flush(self, cache_path, sample):
        cache = HashCache(cache_path)
        cache.put(sample, size=3, mtime_ns=7, md5="m")
        assert cache.get(sample, size=3, mtime_ns=7) == "m"
        assert not cache_path.exists()

    @pytest.mark.parametrize(("size", "mtime_ns"), [(4, 7), (3, 8)])
    def test_changed_size_or_mtime_is_a_miss(self, cache_path, sample, size, mtime_ns):
        cache = HashCache(cache_path)
        cache.put(sample, size=3, mtime_ns=7, md5="m")
        cache.flush()
        assert HashCache(cache_path).get(sample, size=size, mtime_ns=mtime_ns) is None

    def test_flush_merges_with_entries_written_by_another_instance(self, cache_path, tmp_path, sample):
        other = tmp_path / "b.raw"
        first, second = HashCache(cache_path), HashCache(cache_path)
        first.put(sample, size=3, mtime_ns=1, md5="a")
        second.put(other, size=3, mtime_ns=2, md5="b")
        first.flush()
        second.flush()
        merged = HashCache(cache_path)
        assert merged.get(sample, size=3, mtime_ns=1) == "a"
        assert merged.get(other, size=3, mtime_ns=2) == "b"

    def test_expired_entries_are_pruned_on_flush(self, cache_path, tmp_path, sample):
        clock = [0.0]
        cache = HashCache(cache_path, ttl_seconds=10, now=lambda: clock[0])
        cache.put(sample, size=3, mtime_ns=1, md5="old")
        cache.flush()
        clock[0] = 100.0
        cache.put(tmp_path / "b.raw", size=1, mtime_ns=1, md5="new")
        cache.flush()
        assert list(json.loads(cache_path.read_text())["entries"]) == [str(tmp_path / "b.raw")]

    def test_file_is_private(self, cache_path, sample):
        cache = HashCache(cache_path)
        cache.put(sample, size=3, mtime_ns=1, md5="m")
        cache.flush()
        assert stat.S_IMODE(cache_path.stat().st_mode) == 0o600

    @pytest.mark.parametrize("content", ["not json", "[]", '{"version": 99, "entries": {}}'])
    def test_unreadable_file_is_a_miss_not_an_error(self, cache_path, sample, content):
        cache_path.write_text(content)
        assert HashCache(cache_path).get(sample, size=3, mtime_ns=1) is None

from __future__ import annotations

import json
import os
import stat

import pytest

from bfabric.oauth._token_cache import TokenCache


@pytest.fixture
def cache(tmp_path):
    return TokenCache(tmp_path / "token.json")


class TestTokenCache:
    def test_load_returns_none_when_missing(self, cache):
        assert cache.load() is None

    def test_save_and_load_roundtrip(self, cache):
        token = {"access_token": "abc", "expires_at": 9999999999}
        cache.save(token)
        assert cache.load() == token

    def test_save_sets_permissions(self, cache):
        cache.save({"access_token": "x"})
        mode = stat.S_IMODE(os.stat(cache._path).st_mode)
        assert mode == 0o600

    def test_save_creates_parent_dirs(self, tmp_path):
        cache = TokenCache(tmp_path / "sub" / "dir" / "token.json")
        cache.save({"access_token": "x"})
        assert cache.load() == {"access_token": "x"}

    def test_load_returns_none_on_corrupt_json(self, cache):
        cache._path.write_text("not json{{{")
        assert cache.load() is None

    def test_load_returns_none_on_non_dict_json(self, cache):
        cache._path.write_text(json.dumps([1, 2, 3]))
        assert cache.load() is None

    def test_clear_removes_file(self, cache):
        cache.save({"access_token": "x"})
        cache.clear()
        assert cache.load() is None
        assert not cache._path.exists()

    def test_clear_when_no_file(self, cache):
        cache.clear()  # should not raise

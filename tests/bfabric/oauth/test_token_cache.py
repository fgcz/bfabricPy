from __future__ import annotations

import json
import os
import stat

import pytest

from bfabric._oauth.token_cache import TokenCache, compute_token_cache_path


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

    def test_save_creates_file_with_secure_permissions(self, tmp_path):
        """File is created with 0o600 from the start (no race window)."""
        cache = TokenCache(tmp_path / "secure.json")
        cache.save({"access_token": "secret"})
        mode = stat.S_IMODE(os.stat(cache._path).st_mode)
        # Must be owner-only from creation, not set after the fact
        assert mode == 0o600
        assert not (mode & stat.S_IRGRP)
        assert not (mode & stat.S_IROTH)

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


class TestComputeTokenCachePath:
    def test_deterministic(self):
        p1 = compute_token_cache_path("https://example.com/bfabric", "my-client", "PROD")
        p2 = compute_token_cache_path("https://example.com/bfabric", "my-client", "PROD")
        assert p1 == p2

    def test_trailing_slash_ignored(self):
        p1 = compute_token_cache_path("https://example.com/bfabric", "c", "PROD")
        p2 = compute_token_cache_path("https://example.com/bfabric/", "c", "PROD")
        assert p1 == p2

    def test_different_client_id_gives_different_path(self):
        p1 = compute_token_cache_path("https://example.com/bfabric", "client-a", "PROD")
        p2 = compute_token_cache_path("https://example.com/bfabric", "client-b", "PROD")
        assert p1 != p2

    def test_different_base_url_gives_different_path(self):
        p1 = compute_token_cache_path("https://prod.example.com/bfabric", "c", "PROD")
        p2 = compute_token_cache_path("https://test.example.com/bfabric", "c", "PROD")
        assert p1 != p2

    def test_different_env_name_gives_different_path(self):
        p1 = compute_token_cache_path("https://example.com/bfabric", "c", "USER")
        p2 = compute_token_cache_path("https://example.com/bfabric", "c", "ADMIN")
        assert p1 != p2

    def test_path_under_bfabric_tokens(self):
        p = compute_token_cache_path("https://example.com/bfabric", "c", "PROD")
        assert p.parent.name == "tokens"
        assert p.parent.parent.name == ".bfabric"
        assert p.suffix == ".json"

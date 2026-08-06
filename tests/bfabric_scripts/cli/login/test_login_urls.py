from __future__ import annotations

import pytest

from bfabric_scripts.cli.login._urls import KNOWN_INSTANCES, normalize_base_url, suggest_env_name


class TestKnownInstances:
    def test_base_urls_are_canonical(self):
        """The table is what a typed URL is canonicalised *to*, so its own entries must be canonical."""
        for url in KNOWN_INSTANCES.values():
            assert url == normalize_base_url(url)


class TestNormalizeBaseUrl:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("https://example.com/bfabric", "https://example.com/bfabric"),
            ("https://example.com/bfabric/", "https://example.com/bfabric"),
            ("  https://example.com/bfabric  ", "https://example.com/bfabric"),
            ("https://EXAMPLE.com/bfabric", "https://example.com/bfabric"),
            ("example.com/bfabric", "https://example.com/bfabric"),
            ("http://example.com/bfabric", "http://example.com/bfabric"),
        ],
    )
    def test_normalizes(self, raw, expected):
        assert normalize_base_url(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        ["fgcz-bfabric-demo.uzh.ch", "FGCZ-BFABRIC-DEMO.uzh.ch", "https://fgcz-bfabric-demo.uzh.ch"],
    )
    def test_expands_a_bare_known_host(self, raw):
        """Host-only matching is what lets a bare host expand to a full base URL."""
        assert normalize_base_url(raw) == "https://fgcz-bfabric-demo.uzh.ch/bfabric"

    def test_keeps_an_explicit_path_on_a_known_host(self):
        """Canonicalisation may add information, never overwrite a path the user typed."""
        assert normalize_base_url("https://fgcz-bfabric-demo.uzh.ch/other") == "https://fgcz-bfabric-demo.uzh.ch/other"

    @pytest.mark.parametrize("raw", ["", "   ", "ftp://example.com", "https://"])
    def test_rejects_unusable_input(self, raw):
        with pytest.raises(ValueError):
            normalize_base_url(raw)


class TestSuggestEnvName:
    def test_uses_the_known_instance_name(self):
        assert suggest_env_name("https://fgcz-bfabric.uzh.ch/bfabric") == "fgcz-prod"

    def test_derives_a_name_from_an_unknown_host(self):
        assert suggest_env_name("https://bfabric.example.com/bfabric") == "bfabric-example-com"

    def test_falls_back_when_there_is_no_host(self):
        assert suggest_env_name("") == "bfabric"

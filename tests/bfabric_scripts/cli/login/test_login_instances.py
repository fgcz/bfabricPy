from __future__ import annotations

import pytest

from bfabric_scripts.cli.login._instances import KNOWN_INSTANCES, match_instance, suggest_env_name


class TestKnownInstances:
    def test_names_are_unique(self):
        names = [instance.name for instance in KNOWN_INSTANCES]
        assert len(set(names)) == len(names)

    def test_base_urls_are_canonical(self):
        """The list is what a typed URL is canonicalised *to*, so its own entries must be canonical."""
        for instance in KNOWN_INSTANCES:
            assert instance.base_url.startswith("https://")
            assert not instance.base_url.endswith("/")
            assert instance.base_url == instance.base_url.lower()


class TestMatchInstance:
    def test_matches_a_full_base_url(self):
        matched = match_instance("https://fgcz-bfabric-demo.uzh.ch/bfabric")
        assert matched is not None
        assert matched.name == "fgcz-demo"

    def test_matches_on_host_alone(self):
        """Host-only matching is what lets a bare host expand to a full base URL."""
        assert match_instance("fgcz-bfabric-demo.uzh.ch") == match_instance("https://fgcz-bfabric-demo.uzh.ch/bfabric")

    def test_matches_case_insensitively(self):
        matched = match_instance("https://FGCZ-BFABRIC-DEMO.uzh.ch/bfabric")
        assert matched is not None
        assert matched.name == "fgcz-demo"

    def test_ignores_the_path(self):
        matched = match_instance("https://fgcz-bfabric-demo.uzh.ch/somewhere-else")
        assert matched is not None
        assert matched.name == "fgcz-demo"

    @pytest.mark.parametrize("raw", ["https://bfabric.example.com/bfabric", "example.com", ""])
    def test_returns_none_for_an_unknown_host(self, raw):
        assert match_instance(raw) is None


class TestSuggestEnvName:
    def test_uses_the_known_instance_name(self):
        assert suggest_env_name("https://fgcz-bfabric.uzh.ch/bfabric") == "fgcz-prod"

    def test_derives_a_name_from_an_unknown_host(self):
        assert suggest_env_name("https://bfabric.example.com/bfabric") == "bfabric-example-com"

    def test_falls_back_when_there_is_no_host(self):
        assert suggest_env_name("") == "bfabric"

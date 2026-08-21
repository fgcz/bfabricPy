import pickle

import pytest
import yaml
from pydantic import ValidationError

from bfabric.config import BfabricClientConfig, BaseUrl


class TestCanonicalisation:
    @pytest.mark.parametrize(
        "raw",
        [
            "https://example.com/bfabric",
            "https://example.com/bfabric/",
            "https://example.com/bfabric////",
        ],
    )
    def test_drops_trailing_slashes(self, raw):
        assert BaseUrl(raw) == "https://example.com/bfabric"

    def test_host_only_url_keeps_no_slash(self):
        # AnyHttpUrl re-adds the slash for an empty path, so the strip has to happen after validation.
        assert BaseUrl("https://example.com") == "https://example.com"

    def test_normalizes_host_case_and_default_port(self):
        assert BaseUrl("https://EXAMPLE.com:443/bfabric") == "https://example.com/bfabric"

    def test_is_idempotent(self):
        once = BaseUrl("https://example.com/bfabric/")
        assert BaseUrl(once) == once

    @pytest.mark.parametrize("raw", ["not a url", "", "ftp://example.com/bfabric"])
    def test_rejects_non_http_url(self, raw):
        # A plain ValueError, not a pydantic ValidationError: the CLI prints this straight to the user.
        with pytest.raises(ValueError, match="Not a valid http"):
            BaseUrl(raw)

    def test_rejection_surfaces_as_a_validation_error_on_a_model(self):
        # Pydantic wraps a validator's ValueError, so model errors keep their usual shape.
        with pytest.raises(ValidationError):
            BfabricClientConfig.model_validate({"base_url": "not a url"})


class TestBehavesLikeStr:
    """The reason this is a ``str`` subclass rather than a wrapper model."""

    def test_interpolates_without_ceremony(self):
        url = BaseUrl("https://example.com/bfabric")
        assert f"{url}/rest/oauth/token" == "https://example.com/bfabric/rest/oauth/token"

    def test_compares_and_hashes_as_str(self):
        url = BaseUrl("https://example.com/bfabric/")
        assert url == "https://example.com/bfabric"
        assert {url: 1}["https://example.com/bfabric"] == 1

    def test_survives_pickling(self):
        url = BaseUrl("https://example.com/bfabric")
        assert pickle.loads(pickle.dumps(url)) == url


class TestOnTheConfigModel:
    def test_field_is_canonicalised(self):
        config = BfabricClientConfig(base_url=BaseUrl("https://example.com/bfabric/"))
        assert config.base_url == "https://example.com/bfabric"
        assert isinstance(config.base_url, BaseUrl)

    def test_model_validate_accepts_a_plain_string(self):
        # The config is the boundary where un-canonicalised input legitimately arrives.
        config = BfabricClientConfig.model_validate({"base_url": "https://example.com/bfabric/"})
        assert config.base_url == "https://example.com/bfabric"

    def test_json_dump_yields_a_plain_str(self):
        config = BfabricClientConfig.model_validate({"base_url": "https://example.com/bfabric"})
        dumped = config.model_dump(mode="json")
        assert type(dumped["base_url"]) is str

    def test_json_dump_is_yaml_safe_dumpable(self):
        """Guards the trap: a str subclass reaching a yaml dumper writes an unloadable file.

        ``yaml.safe_dump`` raises on a subclass and plain ``yaml.dump`` silently emits a
        ``!!python/object/new:`` tag, so anything bound for YAML must go through json-mode dumping.
        """
        config = BfabricClientConfig.model_validate({"base_url": "https://example.com/bfabric"})
        serialized = yaml.safe_dump(config.model_dump(mode="json"))
        assert yaml.safe_load(serialized)["base_url"] == "https://example.com/bfabric"

    def test_round_trip_dump_reloads(self):
        config = BfabricClientConfig.model_validate({"base_url": "https://example.com/bfabric"})
        dumped = config.model_dump(mode="json", round_trip=True)
        assert BfabricClientConfig.model_validate(dumped) == config

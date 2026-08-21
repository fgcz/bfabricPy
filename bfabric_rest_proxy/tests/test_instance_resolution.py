"""Tests for the instance-URL settings and the ``bfabric_instance`` dependency."""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from bfabric import BfabricAuth
from bfabric_rest_proxy.server import get_bfabric_instance
from bfabric_rest_proxy.settings import ServerSettings

INSTANCE = "https://test.bfabric.example.com/bfabric"


def build_settings(**overrides: object) -> ServerSettings:
    defaults = dict(
        validation_bfabric_instance=INSTANCE,
        supported_bfabric_instances=[INSTANCE],
        feeder_user_credentials={INSTANCE: BfabricAuth(login="feeder", password=SecretStr("x" * 32))},
        default_bfabric_instance=INSTANCE,
    )
    return ServerSettings(**{**defaults, **overrides})  # pyright: ignore[reportCallIssue]


class TestServerSettings:
    @pytest.mark.parametrize("default", [INSTANCE, f"{INSTANCE}/"])
    def test_accepts_either_default_instance_form(self, default):
        assert build_settings(default_bfabric_instance=default).default_bfabric_instance == INSTANCE

    def test_rejects_an_unsupported_default_instance(self):
        with pytest.raises(ValidationError, match="must be one of supported_bfabric_instances"):
            build_settings(default_bfabric_instance="https://other.example.com/bfabric")

    def test_allows_no_default_instance(self):
        assert build_settings(default_bfabric_instance=None).default_bfabric_instance is None


class TestGetBfabricInstance:
    @pytest.mark.parametrize("requested", [INSTANCE, f"{INSTANCE}/"])
    def test_accepts_either_requested_form(self, requested):
        settings = build_settings()
        assert get_bfabric_instance(settings, requested) == INSTANCE

    def test_falls_back_to_the_default(self):
        assert get_bfabric_instance(build_settings(), None) == INSTANCE

    def test_rejects_an_unknown_instance(self):
        with pytest.raises(ValueError, match="Unknown bfabric instance"):
            get_bfabric_instance(build_settings(), "https://other.example.com/bfabric")

    def test_rejects_a_malformed_instance(self):
        with pytest.raises(ValueError, match="Not a valid http"):
            get_bfabric_instance(build_settings(), "not-a-url")

    def test_requires_an_instance_when_no_default_is_configured(self):
        with pytest.raises(ValueError, match="explicit bfabric_instance"):
            get_bfabric_instance(build_settings(default_bfabric_instance=None), None)

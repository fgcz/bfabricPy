"""Invariants the config layer's callers depend on, which no single module's tests cover."""

from __future__ import annotations

import copy
import json

from pydantic import SecretStr

from bfabric.config import BfabricAuth, BfabricClientConfig
from bfabric.config.config_data import ConfigData, export_config_data
from bfabric.config.config_file import ConfigFile, EnvironmentConfig


class TestExportCoversEveryField:
    def test_export_covers_the_override_wire_format(self):
        """BFABRICPY_CONFIG_OVERRIDE is a cross-process contract: no key may silently vanish."""
        config_data = ConfigData(
            client=BfabricClientConfig(base_url="https://example.com/bfabric"),
            auth=BfabricAuth(login="user", password=SecretStr("p" * 32)),
            auth_method="oauth",
            client_id="CLI",
            env_name="PROD",
        )
        assert set(json.loads(export_config_data(config_data))) == {
            "client",
            "auth",
            "auth_method",
            "client_id",
            "client_secret",
            "scope",
            "env_name",
        }


class TestReaderDoesNotMutateInput:
    """The writers pass the mapping they are about to persist through the reader to validate it."""

    def test_config_file_validate_leaves_input_untouched(self):
        raw = {
            "GENERAL": {"default_config": "PROD"},
            "PROD": {"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "token"},
        }
        before = copy.deepcopy(raw)
        _ = ConfigFile.model_validate(raw)
        assert raw == before

    def test_environment_config_validate_leaves_input_untouched(self):
        raw = {"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "token"}
        before = copy.deepcopy(raw)
        _ = EnvironmentConfig.model_validate(raw)
        assert raw == before

import os

import pytest

from bfabric import BfabricClientConfig, BfabricAuth
from bfabric.config.config_data import ConfigData, export_config_data, load_config_data


@pytest.fixture
def client_config():
    return BfabricClientConfig(base_url="https://example.com")


@pytest.fixture
def auth_config():
    return BfabricAuth(login="test-dummy", password="y" * 32)


@pytest.fixture
def config_data(client_config, auth_config):
    return ConfigData(client=client_config, auth=auth_config)


def test_load_config_from_env(mocker, config_data):
    mocker.patch.dict(os.environ, {"BFABRICPY_CONFIG_DATA": export_config_data(config_data)})
    loaded_config = load_config_data()
    assert loaded_config == config_data


def test_export_roundtrip(config_data):
    exported = export_config_data(config_data)
    loaded_config = ConfigData.model_validate_json(exported)
    assert loaded_config == config_data

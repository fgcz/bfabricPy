"""Shared fixtures for bfabric_rest_proxy tests.

This module provides fixtures that mock Bfabric client and settings to ensure
no real API calls are made during testing.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from bfabric import Bfabric, BfabricAuth
from bfabric.config.config_data import ConfigData
from bfabric.results.result_container import ResultContainer
from bfabric_rest_proxy.server import (
    app,
    get_bfabric_feeder_client,
    get_bfabric_instance,
    get_bfabric_user_client,
    get_server_settings,
)
from bfabric_rest_proxy.settings import ServerSettings


@pytest.fixture
def mock_settings():
    """Mock ServerSettings for testing."""
    settings = MagicMock(spec=ServerSettings)
    settings.default_bfabric_instance = "https://test.bfabric.example.com/"
    settings.supported_bfabric_instances = ["https://test.bfabric.example.com/"]
    # BfabricAuth requires passwords of at least 32 characters
    settings.feeder_user_credentials = {
        "https://test.bfabric.example.com/": BfabricAuth(login="feeder_user", password=SecretStr("x" * 32))
    }
    return settings


@pytest.fixture
def mock_bfabric_user_client(mocker):
    """Mock Bfabric user client for testing.

    This ensures no real API calls are made. The mock client's read() and save()
    methods return ResultContainer objects with mock data.
    """
    client = mocker.MagicMock(spec=Bfabric)
    # BfabricAuth requires passwords of at least 32 characters
    client.auth = BfabricAuth(login="test_user", password=SecretStr("y" * 32))
    client.config.base_url = "https://test.bfabric.example.com/"

    # Mock read() to return a ResultContainer with empty results by default
    client.read.return_value = ResultContainer([], total_pages_api=0, errors=[])

    return client


@pytest.fixture
def mock_bfabric_feeder_client(mocker):
    """Mock Bfabric feeder client for testing.

    This ensures no real API calls are made. The mock client's save() method
    returns ResultContainer objects with mock data.
    """
    client = mocker.MagicMock(spec=Bfabric)
    # BfabricAuth requires passwords of at least 32 characters
    client.auth = BfabricAuth(login="feeder_user", password=SecretStr("z" * 32))
    client.config.base_url = "https://test.bfabric.example.com/"

    # Mock save() to return a ResultContainer with mock data by default
    client.save.return_value = ResultContainer([{"id": 1}], total_pages_api=1, errors=[])

    # Mock read() for container access checks
    client.read.return_value = ResultContainer([{"id": 100}], total_pages_api=1, errors=[])

    return client


@pytest.fixture
def client(mock_settings, mock_bfabric_user_client, mock_bfabric_feeder_client):
    """FastAPI test client with mocked dependencies.

    This overrides all FastAPI dependencies to ensure no real B-Fabric API calls
    are made during testing.
    """
    # Override all dependencies
    app.dependency_overrides[get_server_settings] = lambda: mock_settings
    app.dependency_overrides[get_bfabric_instance] = lambda: "https://test.bfabric.example.com/"
    app.dependency_overrides[get_bfabric_user_client] = lambda: mock_bfabric_user_client
    app.dependency_overrides[get_bfabric_feeder_client] = lambda: mock_bfabric_feeder_client

    with TestClient(app) as test_client:
        yield test_client

    # Clean up dependency overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def mock_token_data():
    """Mock TokenData for testing /validate_token endpoint."""
    from bfabric.rest.token_data import TokenData

    return TokenData(
        job_id=1,
        application_id=2,
        entity_class="Dataset",
        entity_id=3,
        user="test_user",
        user_ws_password=SecretStr("a" * 32),
        token_expires="2025-12-31T23:59:59Z",
        web_service_user="true",
        caller="https://test.bfabric.example.com/",
        environment="test",
    )

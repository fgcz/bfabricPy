"""Integration tests for /create/workunit/v1 endpoint.

This module tests the workunit creation endpoint with mocked Bfabric client
to ensure no real API calls are made during testing.
"""

from unittest.mock import MagicMock, patch

import pytest
from bfabric.results.result_container import ResultContainer


class TestCreateWorkunitEndpoint:
    """Tests for the /create/workunit/v1 endpoint."""

    def test_create_workunit_success(self, client, mock_bfabric_user_client, mock_bfabric_feeder_client):
        """Test successful workunit creation."""
        # Mock the create_workunit function to return a mock Workunit
        mock_workunit = MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test Workunit", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        with patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit):
            response = client.post(
                "/create/workunit/v1",
                json={
                    "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                    "params": {
                        "container_id": 100,
                        "application_id": 5,
                        "workunit_name": "Test Workunit",
                        "parameters": {"param1": "value1"},
                        "resources": {},
                        "links": {},
                    },
                },
            )

        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()

        # Response should be a list with the created workunit
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 1

    def test_create_workunit_with_parameters(self, client, mock_bfabric_user_client, mock_bfabric_feeder_client):
        """Test workunit creation with parameters."""
        # Mock the create_workunit function
        mock_workunit = MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test with Params", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        with patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit):
            response = client.post(
                "/create/workunit/v1",
                json={
                    "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                    "params": {
                        "container_id": 100,
                        "application_id": 5,
                        "workunit_name": "Test with Params",
                        "parameters": {"param1": "value1", "param2": "value2"},
                        "resources": {},
                        "links": {},
                    },
                },
            )

        assert response.status_code == 200, f"Response: {response.text}"

    def test_create_workunit_with_resources(self, client, mock_bfabric_user_client, mock_bfabric_feeder_client):
        """Test workunit creation with resources."""
        # Mock the create_workunit function
        mock_workunit = MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test with Resources", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        with patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit):
            response = client.post(
                "/create/workunit/v1",
                json={
                    "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                    "params": {
                        "container_id": 100,
                        "application_id": 5,
                        "workunit_name": "Test with Resources",
                        "parameters": {},
                        "resources": {"resource1": "base64encodeddata"},
                        "links": {},
                    },
                },
            )

        assert response.status_code == 200, f"Response: {response.text}"

    def test_create_workunit_with_links(self, client, mock_bfabric_user_client, mock_bfabric_feeder_client):
        """Test workunit creation with links."""
        # Mock the create_workunit function
        mock_workunit = MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test with Links", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        with patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit):
            response = client.post(
                "/create/workunit/v1",
                json={
                    "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                    "params": {
                        "container_id": 100,
                        "application_id": 5,
                        "workunit_name": "Test with Links",
                        "parameters": {},
                        "resources": {},
                        "links": {"GitHub": "https://github.com/example"},
                    },
                },
            )

        assert response.status_code == 200, f"Response: {response.text}"

    def test_create_workunit_container_access_denied(
        self, client, mock_bfabric_user_client, mock_bfabric_feeder_client
    ):
        """Test that workunit creation fails if user lacks container access."""
        # Mock container access check returns empty (access denied)
        mock_bfabric_user_client.read.return_value = ResultContainer([], total_pages_api=0, errors=[])

        # RuntimeError is raised when container access check fails
        with pytest.raises(RuntimeError, match="Container authorization failed"):
            client.post(
                "/create/workunit/v1",
                json={
                    "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                    "params": {
                        "container_id": 999,  # Non-existent or no access
                        "application_id": 5,
                        "workunit_name": "Test",
                        "parameters": {"p": "v"},
                        "resources": {},
                        "links": {},
                    },
                },
            )

        # Verify feeder client was NOT called (access denied before creation)
        assert not mock_bfabric_feeder_client.save.called

    def test_create_workunit_missing_required_fields(self, client):
        """Test that missing required fields are rejected."""
        response = client.post(
            "/create/workunit/v1",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                # Missing container_id, application_id, workunit_name, parameters/resources/links
                "params": {},
            },
        )

        # Should return validation error
        assert response.status_code == 422

    def test_create_workunit_uses_both_clients(self, client, mock_bfabric_user_client, mock_bfabric_feeder_client):
        """Test that workunit creation passes both user and feeder clients."""
        # Mock the create_workunit function
        mock_workunit = MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        with patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit) as mock_create:
            client.post(
                "/create/workunit/v1",
                json={
                    "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                    "params": {
                        "container_id": 100,
                        "application_id": 5,
                        "workunit_name": "Test",
                        "parameters": {"p": "v"},
                        "resources": {},
                        "links": {},
                    },
                },
            )

            # Verify create_workunit was called with both clients
            assert mock_create.called
            assert mock_create.call_args[1]["user_client"] == mock_bfabric_user_client
            assert mock_create.call_args[1]["feeder_client"] == mock_bfabric_feeder_client

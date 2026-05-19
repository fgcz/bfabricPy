"""Integration tests for /create/workunit/v1 endpoint.

This module tests the workunit creation endpoint with mocked Bfabric client
to ensure no real API calls are made during testing.
"""

import pytest
from bfabric.results.result_container import ResultContainer


class TestCreateWorkunitEndpoint:
    """Tests for the /create/workunit/v1 endpoint."""

    def test_create_workunit_success(self, client, mock_bfabric_user_client, mock_bfabric_feeder_client, mocker):
        """Test successful workunit creation."""
        mock_workunit = mocker.MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test Workunit", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        mocker.patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit)

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

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 1

    def test_create_workunit_with_parameters(
        self, client, mock_bfabric_user_client, mock_bfabric_feeder_client, mocker
    ):
        """Test workunit creation with parameters."""
        mock_workunit = mocker.MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test with Params", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        mocker.patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit)

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

    def test_create_workunit_with_resources(self, client, mock_bfabric_user_client, mock_bfabric_feeder_client, mocker):
        """Test workunit creation with resources."""
        mock_workunit = mocker.MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test with Resources", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        mocker.patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit)

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

    def test_create_workunit_with_links(self, client, mock_bfabric_user_client, mock_bfabric_feeder_client, mocker):
        """Test workunit creation with links."""
        mock_workunit = mocker.MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test with Links", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        mocker.patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit)

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
        mock_bfabric_user_client.read.return_value = ResultContainer([], total_pages_api=0, errors=[])

        with pytest.raises(RuntimeError, match="Container authorization failed"):
            client.post(
                "/create/workunit/v1",
                json={
                    "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                    "params": {
                        "container_id": 999,
                        "application_id": 5,
                        "workunit_name": "Test",
                        "parameters": {"p": "v"},
                        "resources": {},
                        "links": {},
                    },
                },
            )

        assert not mock_bfabric_feeder_client.save.called

    def test_create_workunit_missing_required_fields(self, client):
        """Test that missing required fields are rejected."""
        response = client.post(
            "/create/workunit/v1",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                "params": {},
            },
        )

        assert response.status_code == 422

    def test_create_workunit_uses_both_clients(
        self, client, mock_bfabric_user_client, mock_bfabric_feeder_client, mocker
    ):
        """Test that workunit creation passes both user and feeder clients."""
        mock_workunit = mocker.MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        mock_create = mocker.patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit)

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

        assert mock_create.called
        assert mock_create.call_args[1]["user_client"] == mock_bfabric_user_client
        assert mock_create.call_args[1]["feeder_client"] == mock_bfabric_feeder_client

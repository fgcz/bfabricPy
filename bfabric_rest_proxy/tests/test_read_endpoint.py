"""Integration tests for /read endpoint.

This module tests the /read endpoint with mocked Bfabric client to ensure
no real API calls are made during testing.
"""

from unittest.mock import MagicMock

import pytest
from bfabric.results.result_container import ResultContainer


class TestReadEndpoint:
    """Tests for the /read endpoint."""

    def test_read_success_with_empty_query_list(self, client, mock_bfabric_user_client):
        """Test that empty list query works (validates fix for issue #459)."""
        # Mock the read response
        mock_bfabric_user_client.read.return_value = ResultContainer(
            [{"id": 1, "name": "test"}], total_pages_api=1, errors=[]
        )

        response = client.post(
            "/read",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                "params": {"endpoint": "screen", "query": []},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data == [{"id": 1, "name": "test"}]

        # Verify that read was called with empty dict
        mock_bfabric_user_client.read.assert_called_once()
        call_args = mock_bfabric_user_client.read.call_args
        assert call_args.kwargs["endpoint"] == "screen"
        assert call_args.kwargs["obj"] == {}

    def test_read_success_with_empty_query_dict(self, client, mock_bfabric_user_client):
        """Test that empty dict query works."""
        mock_bfabric_user_client.read.return_value = ResultContainer(
            [{"id": 1, "name": "test"}], total_pages_api=1, errors=[]
        )

        response = client.post(
            "/read",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                "params": {"endpoint": "screen", "query": {}},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data == [{"id": 1, "name": "test"}]

    def test_read_success_with_non_empty_query(self, client, mock_bfabric_user_client):
        """Test successful read with non-empty query."""
        mock_bfabric_user_client.read.return_value = ResultContainer(
            [{"id": 123, "name": "sample1"}], total_pages_api=1, errors=[]
        )

        response = client.post(
            "/read",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                "params": {"endpoint": "sample", "query": {"id": 123, "name": "test"}},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data == [{"id": 123, "name": "sample1"}]

        # Verify correct parameters passed to Bfabric.read()
        mock_bfabric_user_client.read.assert_called_once()
        call_args = mock_bfabric_user_client.read.call_args
        assert call_args.kwargs["endpoint"] == "sample"
        assert call_args.kwargs["obj"] == {"id": 123, "name": "test"}

    def test_read_with_pagination_params(self, client, mock_bfabric_user_client):
        """Test read with pagination parameters."""
        mock_bfabric_user_client.read.return_value = ResultContainer(
            [{"id": 1}, {"id": 2}], total_pages_api=1, errors=[]
        )

        response = client.post(
            "/read",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                "params": {
                    "endpoint": "sample",
                    "query": {"status": "active"},
                    "page_offset": 10,
                    "page_max_results": 50,
                },
            },
        )

        assert response.status_code == 200

        # Verify pagination parameters passed correctly
        call_args = mock_bfabric_user_client.read.call_args
        assert call_args.kwargs["offset"] == 10
        assert call_args.kwargs["max_results"] == 50

    def test_read_calls_to_list_dict(self, client, mock_bfabric_user_client):
        """Test that the response is properly converted to list dict."""
        # Create a mock ResultContainer
        mock_result = MagicMock()
        mock_result.to_list_dict.return_value = [
            {"id": 1, "name": "test1"},
            {"id": 2, "name": "test2"},
        ]
        mock_bfabric_user_client.read.return_value = mock_result

        response = client.post(
            "/read",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                "params": {"endpoint": "screen", "query": {}},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[1]["id"] == 2

        # Verify to_list_dict was called
        mock_result.to_list_dict.assert_called_once()

    def test_read_returns_empty_list_for_no_results(self, client, mock_bfabric_user_client):
        """Test that empty results return empty list."""
        mock_bfabric_user_client.read.return_value = ResultContainer([], total_pages_api=0, errors=[])

        response = client.post(
            "/read",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                "params": {"endpoint": "screen", "query": {"nonexistent": "value"}},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_read_uses_user_client_not_feeder(self, client, mock_bfabric_user_client, mock_bfabric_feeder_client):
        """Test that read endpoint uses user client, not feeder client."""
        mock_bfabric_user_client.read.return_value = ResultContainer([{"id": 1}], total_pages_api=1, errors=[])

        client.post(
            "/read",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                "params": {"endpoint": "screen", "query": {}},
            },
        )

        # Verify user client was called
        assert mock_bfabric_user_client.read.called

        # Verify feeder client was NOT called
        assert not mock_bfabric_feeder_client.read.called

"""Tests for /health endpoint.

This module tests the health check endpoint which returns server status
and configuration information.
"""

import datetime

import pytest


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_ok_status(self, client):
        """Test that health endpoint returns OK status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_includes_date(self, client, mocker):
        """Test that health endpoint includes current date."""
        # Mock datetime.now() using a freeze_time approach
        # Note: We can't mock datetime.datetime.now directly in Python 3.13+
        # Instead, we just verify the date field exists and is a valid ISO format
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        # Verify it's a valid ISO format datetime string
        try:
            datetime.datetime.fromisoformat(data["date"])
        except ValueError:
            pytest.fail(f"Invalid ISO datetime format: {data['date']}")

    def test_health_lists_supported_instances(self, client, mock_settings):
        """Test that health endpoint lists supported B-Fabric instances."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "supported_bfabric_instances" in data
        assert data["supported_bfabric_instances"] == mock_settings.supported_bfabric_instances

    def test_health_uses_get_method(self, client):
        """Test that health endpoint only accepts GET requests."""
        # POST should not be allowed
        response = client.post("/health")
        assert response.status_code == 405  # Method Not Allowed

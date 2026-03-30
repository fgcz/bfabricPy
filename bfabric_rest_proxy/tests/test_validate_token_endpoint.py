"""Integration tests for /validate_token endpoint.

This module tests the token validation endpoint with mocked token validation
to ensure no real API calls are made during testing.
"""

import pytest


class TestValidateTokenEndpoint:
    """Tests for the /validate_token endpoint."""

    @pytest.mark.asyncio
    async def test_validate_token_success(self, client, mock_settings, mock_token_data, mocker):
        """Test successful token validation."""
        mocker.patch(
            "bfabric_rest_proxy.server.get_token_data_async",
            return_value=mock_token_data,
        )

        response = client.post(
            "/validate_token",
            json={"token": "valid_token_123"},
            params={"bfabric_instance": "https://test.bfabric.example.com/"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["jobId"] == mock_token_data.job_id
        assert data["applicationId"] == mock_token_data.application_id
        assert data["entityClassName"] == mock_token_data.entity_class
        assert data["entityId"] == mock_token_data.entity_id
        assert data["user"] == mock_token_data.user
        assert data["userWsPassword"] == "a" * 32
        assert data["expiryDateTime"] == "2025-12-31T23:59:59Z"
        assert data["webServiceUser"] == mock_token_data.web_service_user
        assert data["caller"] == mock_token_data.caller
        assert data["environment"] == mock_token_data.environment

    @pytest.mark.asyncio
    async def test_validate_token_calls_async_function(self, client, mock_token_data, mocker):
        """Test that validate_token calls get_token_data_async with correct parameters."""
        mock_get_token = mocker.patch(
            "bfabric_rest_proxy.server.get_token_data_async",
            return_value=mock_token_data,
        )

        client.post(
            "/validate_token",
            json={"token": "test_token"},
            params={"bfabric_instance": "https://test.bfabric.example.com/"},
        )

        mock_get_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_token_expired_token(self, client, mocker):
        """Test validation with invalid/expired token."""
        mocker.patch(
            "bfabric_rest_proxy.server.get_token_data_async",
            side_effect=Exception("Token validation failed"),
        )

        with pytest.raises(Exception, match="Token validation failed"):
            client.post(
                "/validate_token",
                json={"token": "expired_token"},
                params={"bfabric_instance": "https://test.bfabric.example.com/"},
            )

    @pytest.mark.asyncio
    async def test_validate_token_missing_bfabric_instance(self, client, mock_settings, mock_token_data, mocker):
        """Test that missing bfabric_instance parameter uses default when available."""
        mock_get_token = mocker.patch(
            "bfabric_rest_proxy.server.get_token_data_async",
            return_value=mock_token_data,
        )

        mock_settings.default_bfabric_instance = "https://test.bfabric.example.com/"

        response = client.post(
            "/validate_token",
            json={"token": "test_token"},
        )

        assert response.status_code == 200
        mock_get_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_token_uses_default_instance(self, client, mock_settings, mock_token_data, mocker):
        """Test that default instance is used when not specified."""
        mocker.patch(
            "bfabric_rest_proxy.server.get_token_data_async",
            return_value=mock_token_data,
        )

        mock_settings.default_bfabric_instance = "https://test.bfabric.example.com/"

        response = client.post(
            "/validate_token",
            json={"token": "test_token"},
        )

        assert response.status_code == 200

"""Integration tests for /validate_token endpoint.

This module tests the token validation endpoint with mocked token validation
to ensure no real API calls are made during testing.
"""

import pytest
from pydantic import SecretStr


class TestValidateTokenEndpoint:
    """Tests for the /validate_token endpoint."""

    @pytest.mark.asyncio
    async def test_validate_token_success(self, client, mock_settings, mock_token_data, mocker):
        """Test successful token validation."""
        # Mock get_token_data_async to return test token data
        mock_get_token = mocker.patch(
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

        # Verify token data fields are in response (using camelCase aliases)
        assert "jobId" in data
        assert "applicationId" in data
        assert "user" in data
        assert "caller" in data
        assert data["user"] == "test_user"
        assert data["caller"] == "https://test.bfabric.example.com/"

        # Verify password is included and matches (it's the 32-char test password)
        assert "userWsPassword" in data
        assert data["userWsPassword"] == "a" * 32

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

        # Verify get_token_data_async was called
        mock_get_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_token_expired_token(self, client, mocker):
        """Test validation with invalid/expired token."""
        # Mock get_token_data_async to raise an exception for invalid token
        mocker.patch(
            "bfabric_rest_proxy.server.get_token_data_async",
            side_effect=Exception("Token validation failed"),
        )

        # Exception is raised when token validation fails
        with pytest.raises(Exception, match="Token validation failed"):
            client.post(
                "/validate_token",
                json={"token": "expired_token"},
                params={"bfabric_instance": "https://test.bfabric.example.com/"},
            )

    @pytest.mark.asyncio
    async def test_validate_token_missing_bfabric_instance(self, client, mock_settings, mock_token_data, mocker):
        """Test that missing bfabric_instance parameter uses default when available."""
        # Mock get_token_data_async
        mock_get_token = mocker.patch(
            "bfabric_rest_proxy.server.get_token_data_async",
            return_value=mock_token_data,
        )

        # Mock settings has a default instance
        mock_settings.default_bfabric_instance = "https://test.bfabric.example.com/"

        response = client.post(
            "/validate_token",
            json={"token": "test_token"},
        )

        # Should succeed using default instance
        assert response.status_code == 200
        mock_get_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_token_uses_default_instance(self, client, mock_settings, mock_token_data, mocker):
        """Test that default instance is used when not specified."""
        mock_get_token = mocker.patch(
            "bfabric_rest_proxy.server.get_token_data_async",
            return_value=mock_token_data,
        )

        # Mock settings to have a default instance
        mock_settings.default_bfabric_instance = "https://test.bfabric.example.com/"

        response = client.post(
            "/validate_token",
            json={"token": "test_token"},
        )

        # Should succeed using default instance
        assert response.status_code == 200

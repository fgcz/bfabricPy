"""Integration tests for /validate_token endpoint.

This module tests the token validation endpoint with mocked token validation
to ensure no real API calls are made during testing.
"""

import pytest

from bfabric.errors import BfabricInstanceNotConfiguredError


class TestValidateTokenEndpoint:
    """Tests for the /validate_token endpoint."""

    @pytest.mark.asyncio
    async def test_validate_token_success(self, client, mock_settings, mock_token_data, mocker):
        """Test successful token validation."""
        mocker.patch(
            "bfabric_rest_proxy.server.validate_token",
            return_value=mock_token_data,
        )

        response = client.post(
            "/validate_token",
            json={"token": "valid_token_123"},
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
    async def test_validate_token_calls_with_settings(self, client, mock_settings, mock_token_data, mocker):
        """Test that validate_token is called with settings (not client-provided instance)."""
        mock_validate = mocker.patch(
            "bfabric_rest_proxy.server.validate_token",
            return_value=mock_token_data,
        )

        client.post(
            "/validate_token",
            json={"token": "test_token"},
        )

        mock_validate.assert_called_once()
        call_kwargs = mock_validate.call_args[1]
        assert call_kwargs["settings"] is mock_settings

    @pytest.mark.asyncio
    async def test_validate_token_expired_token(self, client, mock_settings, mocker):
        """Test validation with invalid/expired token."""
        mocker.patch(
            "bfabric_rest_proxy.server.validate_token",
            side_effect=Exception("Token validation failed"),
        )

        with pytest.raises(Exception, match="Token validation failed"):
            client.post(
                "/validate_token",
                json={"token": "expired_token"},
            )

    @pytest.mark.asyncio
    async def test_validate_token_unsupported_instance(self, client, mock_settings, mocker):
        """Test that tokens from unsupported instances are rejected."""
        mocker.patch(
            "bfabric_rest_proxy.server.validate_token",
            side_effect=BfabricInstanceNotConfiguredError("https://evil.example.com/"),
        )

        with pytest.raises(BfabricInstanceNotConfiguredError):
            client.post(
                "/validate_token",
                json={"token": "test_token"},
            )

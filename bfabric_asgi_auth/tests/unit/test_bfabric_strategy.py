"""Unit tests for the B-Fabric token-validation strategy."""

from __future__ import annotations

import pytest
from bfabric.errors import BfabricInstanceNotConfiguredError
from httpx import HTTPError
from pydantic import SecretStr

from bfabric_asgi_auth.token_validation.bfabric_strategy import create_bfabric_validator
from bfabric_asgi_auth.token_validation.strategy import TokenValidationError


@pytest.fixture
def settings(mocker):
    return mocker.MagicMock(name="settings")


class TestBfabricValidator:
    """The happy path is covered end-to-end by the BDD suite; this pins the failure translation."""

    @pytest.mark.parametrize(
        "error",
        [
            HTTPError("boom"),
            BfabricInstanceNotConfiguredError("https://other.example.com/bfabric"),
            # A caller the core rejects as a non-http URL: a failed validation, not a 500.
            ValueError("Not a valid http(s) URL: 'urn:example:nope'"),
        ],
    )
    async def test_reports_a_failure_instead_of_propagating(self, mocker, settings, error):
        mocker.patch("bfabric_asgi_auth.token_validation.bfabric_strategy.validate_token", side_effect=error)
        result = await create_bfabric_validator(settings)(SecretStr("mock-token"))
        assert isinstance(result, TokenValidationError)
        assert "Bfabric token validation failed" in result.error

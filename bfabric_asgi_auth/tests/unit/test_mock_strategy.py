"""Tests for mock OAuth token validation strategy."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from bfabric_asgi_auth.token_validation.mock_strategy import create_mock_oauth_validator


class TestMockOAuthValidatorDeterminism:
    async def test_job_id_is_deterministic_across_instances(self):
        """job_id must not depend on Python's randomised hash seed (PYTHONHASHSEED)."""
        v1 = create_mock_oauth_validator()
        v2 = create_mock_oauth_validator()

        r1 = await v1(SecretStr("valid_alice"))
        r2 = await v2(SecretStr("valid_alice"))

        assert r1.context.job_id == r2.context.job_id  # type: ignore[union-attr]

    async def test_job_id_is_stable_value(self):
        """The job_id for a known username must equal the stable zlib.crc32-based value."""
        import zlib

        expected = zlib.crc32(b"alice") % 100000
        v = create_mock_oauth_validator()
        result = await v(SecretStr("valid_alice"))
        assert result.context.job_id == expected  # type: ignore[union-attr]

    async def test_different_usernames_produce_different_job_ids(self):
        v = create_mock_oauth_validator()
        r_alice = await v(SecretStr("valid_alice"))
        r_bob = await v(SecretStr("valid_bob"))
        assert r_alice.context.job_id != r_bob.context.job_id  # type: ignore[union-attr]

    async def test_invalid_token_returns_error(self):
        v = create_mock_oauth_validator()
        result = await v(SecretStr("invalid_token"))
        assert not result.success

    async def test_valid_token_returns_exchange_success(self):
        from bfabric_asgi_auth.token_validation.strategy import OAuthExchangeSuccess

        v = create_mock_oauth_validator()
        result = await v(SecretStr("valid_test123"))
        assert isinstance(result, OAuthExchangeSuccess)
        assert result.context.subject == "test123"
        assert "access_token" in result.token
        assert "refresh_token" in result.token

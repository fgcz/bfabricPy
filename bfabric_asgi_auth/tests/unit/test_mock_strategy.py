"""Tests for mock token validation strategies."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from bfabric_asgi_auth.token_validation.mock_strategy import create_mock_validator


class TestMockValidatorDeterminism:
    async def test_job_id_is_deterministic_across_instances(self):
        """job_id must not depend on Python's randomised hash seed (PYTHONHASHSEED)."""
        v1 = create_mock_validator()
        v2 = create_mock_validator()

        r1 = await v1(SecretStr("valid_alice"))
        r2 = await v2(SecretStr("valid_alice"))

        assert r1.token_data.job_id == r2.token_data.job_id  # type: ignore[union-attr]

    async def test_job_id_is_stable_value(self):
        """The job_id for a known username must equal the stable zlib.crc32-based value."""
        import zlib

        expected = zlib.crc32(b"alice") % 100000
        v = create_mock_validator()
        result = await v(SecretStr("valid_alice"))
        assert result.token_data.job_id == expected  # type: ignore[union-attr]

    async def test_different_usernames_produce_different_job_ids(self):
        v = create_mock_validator()
        r_alice = await v(SecretStr("valid_alice"))
        r_bob = await v(SecretStr("valid_bob"))
        assert r_alice.token_data.job_id != r_bob.token_data.job_id  # type: ignore[union-attr]

    async def test_invalid_token_returns_error(self):
        v = create_mock_validator()
        result = await v(SecretStr("invalid_token"))
        assert not result.success

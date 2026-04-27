"""Unit tests for token validation error classification on ErrorResponse.invalid_token."""

from __future__ import annotations

import pytest

from bfabric.errors import BfabricTokenValidationFailedError
from bfabric_asgi_auth.response_renderer import ErrorResponse


@pytest.mark.parametrize(
    "error_kind,expected_type",
    [
        ("expired", "token_expired"),
        ("invalid", "token_invalid"),
        ("network", "token_network"),
        ("unknown", "token_unknown"),
        ("garbage", "token_unknown"),
    ],
)
def test_invalid_token_error_kind_to_error_type(error_kind: str, expected_type: str) -> None:
    response = ErrorResponse.invalid_token(error_kind=error_kind)
    assert response.error_type == expected_type
    assert response.status_code == 400


def test_invalid_token_detail_is_appended_to_message() -> None:
    response = ErrorResponse.invalid_token(error_kind="expired", detail="token too old")
    assert "token too old" in response.message


def test_invalid_token_no_detail_uses_default_message() -> None:
    response = ErrorResponse.invalid_token(error_kind="expired")
    assert response.message == "Token has expired"


def test_bfabric_token_validation_failed_error_carries_is_expired_flag() -> None:
    expired = BfabricTokenValidationFailedError.expired_token()
    invalid = BfabricTokenValidationFailedError.invalid_token()
    plain = BfabricTokenValidationFailedError("some other failure")

    assert expired.is_expired is True
    assert invalid.is_expired is False
    assert plain.is_expired is False

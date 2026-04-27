"""Unit tests for token validation error classification on ErrorResponse.invalid_token."""

from __future__ import annotations

import pytest

from bfabric.errors import (
    BfabricTokenExpiredError,
    BfabricTokenInvalidError,
    BfabricTokenValidationFailedError,
)
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


def test_token_expired_error_is_a_validation_failed_error() -> None:
    expired = BfabricTokenExpiredError()
    invalid = BfabricTokenInvalidError()

    assert isinstance(expired, BfabricTokenValidationFailedError)
    assert isinstance(invalid, BfabricTokenValidationFailedError)
    assert "expired" in str(expired)
    assert "invalid" in str(invalid)


def test_token_subclass_constructors_accept_custom_message() -> None:
    expired = BfabricTokenExpiredError("custom: token aged out")
    assert "custom: token aged out" in str(expired)


def test_subclasses_are_distinguishable_via_isinstance() -> None:
    expired = BfabricTokenExpiredError()
    invalid = BfabricTokenInvalidError()

    assert isinstance(expired, BfabricTokenExpiredError)
    assert not isinstance(expired, BfabricTokenInvalidError)
    assert isinstance(invalid, BfabricTokenInvalidError)
    assert not isinstance(invalid, BfabricTokenExpiredError)

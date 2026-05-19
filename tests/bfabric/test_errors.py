from __future__ import annotations

from bfabric.errors import BfabricTokenExpiredError, BfabricTokenInvalidError, BfabricTokenValidationFailedError


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

from __future__ import annotations

from types import SimpleNamespace

from bfabric.errors import (
    BfabricRequestError,
    BfabricTokenExpiredError,
    BfabricTokenInvalidError,
    BfabricTokenValidationFailedError,
    get_response_errors,
)


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


# ---- get_response_errors ----


class TestGetResponseErrorsTopLevel:
    """Branch: response has a top-level errorreport attribute."""

    def test_returns_single_error_for_top_level_report(self) -> None:
        response = SimpleNamespace(errorreport="something went wrong")
        result = get_response_errors(response, "getDataset")

        assert len(result) == 1
        assert isinstance(result[0], BfabricRequestError)
        assert result[0].message == "something went wrong"

    def test_ignores_endpoint_when_top_level_error_present(self) -> None:
        item = SimpleNamespace(errorreport="item error")
        response = SimpleNamespace(errorreport="top", getDataset=[item])
        result = get_response_errors(response, "getDataset")

        assert len(result) == 1
        assert result[0].message == "top"

    def test_errorreport_empty_string_treated_as_no_error(self) -> None:
        response = SimpleNamespace(errorreport="")
        result = get_response_errors(response, "getDataset")

        assert result == []


class TestGetResponseErrorsEndpointLevel:
    """Branch: response[endpoint] is a list of results that may have errorreport."""

    def test_returns_empty_list_when_no_errors(self) -> None:
        item1 = SimpleNamespace(name="ok1")
        item2 = SimpleNamespace(name="ok2")
        response = SimpleNamespace(getDataset=[item1, item2])
        result = get_response_errors(response, "getDataset")

        assert result == []

    def test_returns_error_for_single_failed_item(self) -> None:
        ok = SimpleNamespace(name="ok")
        fail = SimpleNamespace(name="fail", errorreport="bad thing")
        response = SimpleNamespace(getDataset=[ok, fail])
        result = get_response_errors(response, "getDataset")

        assert len(result) == 1
        assert result[0].message == "bad thing"

    def test_returns_error_for_all_failed_items(self) -> None:
        fail1 = SimpleNamespace(errorreport="err1")
        fail2 = SimpleNamespace(errorreport="err2")
        response = SimpleNamespace(getDataset=[fail1, fail2])
        result = get_response_errors(response, "getDataset")

        assert len(result) == 2
        assert result[0].message == "err1"
        assert result[1].message == "err2"

    def test_skips_items_without_errorreport(self) -> None:
        ok1 = SimpleNamespace(name="a")
        fail = SimpleNamespace(name="b", errorreport="fail")
        ok2 = SimpleNamespace(name="c")
        response = SimpleNamespace(getDataset=[ok1, fail, ok2])
        result = get_response_errors(response, "getDataset")

        assert len(result) == 1
        assert result[0].message == "fail"

    def test_errorreport_none_is_skipped(self) -> None:
        item = SimpleNamespace(name="x", errorreport=None)
        response = SimpleNamespace(getDataset=[item])
        result = get_response_errors(response, "getDataset")

        assert result == []

    def test_wrong_endpoint_returns_empty(self) -> None:
        item = SimpleNamespace(errorreport="err")
        response = SimpleNamespace(getDataset=[item])
        result = get_response_errors(response, "getSample")

        assert result == []


class TestGetResponseErrorsNoMatch:
    """Branch: response has neither errorreport nor endpoint key."""

    def test_miserable_dict_returns_empty(self) -> None:
        response = {}
        result = get_response_errors(response, "getDataset")

        assert result == []

    def test_dict_with_other_keys_returns_empty(self) -> None:
        response = {"otherkey": "value"}
        result = get_response_errors(response, "getDataset")

        assert result == []

    def test_response_with_no_endpoint_and_no_error(self) -> None:
        response = SimpleNamespace(other="value")
        result = get_response_errors(response, "getDataset")

        assert result == []

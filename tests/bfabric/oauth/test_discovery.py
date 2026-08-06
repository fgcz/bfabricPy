from __future__ import annotations

import httpx
import pytest

from bfabric._oauth.discovery import DISCOVERY_PATH, fetch_discovery_document, resolve_base_url


def _response(status: int, json_body: object = None) -> httpx.Response:
    if json_body is None:
        return httpx.Response(status, text="nope")
    return httpx.Response(status, json=json_body)


class TestFetchDiscoveryDocument:
    def test_returns_document_on_200(self, mocker):
        get = mocker.patch(
            "bfabric._oauth.discovery.httpx.get",
            return_value=_response(200, {"issuer": "https://example.com/bfabric"}),
        )
        assert fetch_discovery_document("https://example.com/bfabric") == {"issuer": "https://example.com/bfabric"}
        assert get.call_args.args[0] == f"https://example.com/bfabric/{DISCOVERY_PATH}"

    def test_strips_trailing_slash_from_base_url(self, mocker):
        get = mocker.patch("bfabric._oauth.discovery.httpx.get", return_value=_response(200, {"issuer": "x"}))
        _ = fetch_discovery_document("https://example.com/bfabric/")
        assert get.call_args.args[0] == f"https://example.com/bfabric/{DISCOVERY_PATH}"

    def test_returns_none_on_404(self, mocker):
        mocker.patch("bfabric._oauth.discovery.httpx.get", return_value=_response(404))
        assert fetch_discovery_document("https://example.com") is None

    def test_returns_none_on_non_json_body(self, mocker):
        mocker.patch("bfabric._oauth.discovery.httpx.get", return_value=_response(200))
        assert fetch_discovery_document("https://example.com") is None

    def test_returns_none_on_json_that_is_not_an_object(self, mocker):
        mocker.patch("bfabric._oauth.discovery.httpx.get", return_value=_response(200, ["not", "a", "mapping"]))
        assert fetch_discovery_document("https://example.com") is None

    def test_returns_none_on_transport_error(self, mocker):
        """Never raises: a pre-flight that fails closed would make the CLI unusable on a flaky network."""
        mocker.patch("bfabric._oauth.discovery.httpx.get", side_effect=httpx.ConnectError("boom"))
        assert fetch_discovery_document("https://example.com") is None

    def test_returns_none_on_invalid_url(self, mocker):
        mocker.patch("bfabric._oauth.discovery.httpx.get", side_effect=httpx.InvalidURL("bad"))
        assert fetch_discovery_document("http://:::") is None


class TestResolveBaseUrl:
    def test_confirms_a_working_base_url(self, mocker):
        mocker.patch("bfabric._oauth.discovery.fetch_discovery_document", return_value={"issuer": "x"})
        assert resolve_base_url("https://example.com/bfabric") == ("https://example.com/bfabric", True)

    def test_appends_bfabric_when_the_bare_host_has_no_discovery(self, mocker):
        """The likeliest typo: a host without the ``/bfabric`` path segment."""
        fetch = mocker.patch(
            "bfabric._oauth.discovery.fetch_discovery_document",
            side_effect=[None, {"issuer": "x"}],
        )
        assert resolve_base_url("https://example.com") == ("https://example.com/bfabric", True)
        assert [call.args[0] for call in fetch.call_args_list] == ["https://example.com", "https://example.com/bfabric"]

    def test_returns_input_unconfirmed_when_neither_answers(self, mocker):
        """Fails open. A both-miss also covers an instance that doesn't publish the document, so
        raising here would block a login that would have worked."""
        mocker.patch("bfabric._oauth.discovery.fetch_discovery_document", return_value=None)
        assert resolve_base_url("https://example.com/bfabric") == ("https://example.com/bfabric", False)

    def test_does_not_retry_when_the_path_already_ends_in_bfabric(self, mocker):
        fetch = mocker.patch("bfabric._oauth.discovery.fetch_discovery_document", return_value=None)
        assert resolve_base_url("https://example.com/bfabric") == ("https://example.com/bfabric", False)
        assert fetch.call_count == 1

    @pytest.mark.parametrize("raw", ["https://example.com/bfabric/", "https://example.com/bfabric"])
    def test_normalizes_the_trailing_slash(self, mocker, raw):
        mocker.patch("bfabric._oauth.discovery.fetch_discovery_document", return_value={"issuer": "x"})
        assert resolve_base_url(raw)[0] == "https://example.com/bfabric"

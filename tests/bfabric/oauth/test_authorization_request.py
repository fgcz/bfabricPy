from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from pydantic import ValidationError

from bfabric.oauth import AuthorizationRequest
from bfabric.oauth._pkce import _generate_challenge


def build(**overrides) -> AuthorizationRequest:
    kwargs = {
        "client_id": "my-client",
        "redirect_uri": "https://app.example.com/callback",
        "scope": "api:read",
    }
    return AuthorizationRequest.create(
        overrides.pop("base_url", "https://example.com/bfabric"), **{**kwargs, **overrides}
    )


class TestUrl:
    def test_targets_the_authorize_endpoint(self):
        assert build().url.startswith("https://example.com/bfabric/rest/oauth/authorize?")

    def test_carries_the_authorization_request_params(self):
        request = build()
        assert parse_qs(urlparse(request.url).query) == {
            "response_type": ["code"],
            "client_id": ["my-client"],
            "redirect_uri": ["https://app.example.com/callback"],
            "code_challenge": [_generate_challenge(request.verifier)],
            "code_challenge_method": ["S256"],
            "state": [request.state],
            "scope": ["api:read"],
        }

    def test_percent_encodes_the_redirect_uri(self):
        # A raw "&" in the caller's URI would otherwise terminate the value early.
        request = build(redirect_uri="https://app.example.com/cb?a=1&b=2")
        assert parse_qs(urlparse(request.url).query)["redirect_uri"] == ["https://app.example.com/cb?a=1&b=2"]

    def test_rejects_a_non_bfabric_base_url(self):
        with pytest.raises(ValueError):
            build(base_url="https://example.com/notbfabric")


class TestGeneratedSecrets:
    def test_challenge_in_the_url_matches_the_returned_verifier(self):
        # The invariant the caller can no longer get wrong, and the reason this type exists rather
        # than a builder taking a code_challenge: a mismatch here is only ever reported by the
        # server, one redirect later, as an opaque rejection at the token step.
        request = build()
        challenge = parse_qs(urlparse(request.url).query)["code_challenge"][0]
        assert challenge == _generate_challenge(request.verifier)

    def test_verifier_is_within_the_rfc_7636_length_bounds(self):
        assert 43 <= len(build().verifier) <= 128

    def test_each_request_is_unique(self):
        first, second = build(), build()
        assert first.verifier != second.verifier
        assert first.state != second.state


class TestModel:
    def test_is_frozen(self):
        # The verifier and state are carried across a redirect and compared on return; a caller
        # that could mutate them in flight would defeat both PKCE and the CSRF check.
        with pytest.raises(ValidationError):
            build().state = "other"  # pyright: ignore[reportAttributeAccessIssue]

    def test_round_trips_through_a_dict(self):
        # log-viewer persists this in a signed session cookie between the redirect and the callback.
        request = build()
        assert AuthorizationRequest.model_validate(request.model_dump()) == request

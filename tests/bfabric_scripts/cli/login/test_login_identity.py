from __future__ import annotations

import base64
import json

import pytest

from bfabric_scripts.cli.login._identity import (
    UNKNOWN_IDENTITY,
    decode_jwt_payload,
    describe_identity,
    granted_scope,
    token_claims,
)


def _jwt(payload: dict[str, object]) -> str:
    """A JWT-shaped token whose payload is *payload*; the signature is never checked here."""
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{body}.signature"


class TestDecodeJwtPayload:
    def test_decodes_a_payload(self):
        assert decode_jwt_payload(_jwt({"sub": "someone", "scope": "api:read"})) == {
            "sub": "someone",
            "scope": "api:read",
        }

    def test_decodes_a_payload_needing_base64_padding(self):
        # A JWT carries no '=' padding, so a payload of any length must still decode.
        for size in range(1, 6):
            payload = {"sub": "a" * size}
            assert decode_jwt_payload(_jwt(payload)) == payload

    @pytest.mark.parametrize("token", ["", "opaque-token", "only.two", "a.b.c.d"])
    def test_returns_none_for_a_non_jwt(self, token):
        assert decode_jwt_payload(token) is None

    def test_returns_none_when_the_payload_is_not_base64(self):
        assert decode_jwt_payload("header.!!!not-base64!!!.signature") is None

    def test_returns_none_when_the_payload_is_not_json(self):
        body = base64.urlsafe_b64encode(b"not json").decode().rstrip("=")
        assert decode_jwt_payload(f"header.{body}.signature") is None

    def test_returns_none_when_the_payload_is_not_a_json_object(self):
        body = base64.urlsafe_b64encode(b"[1, 2, 3]").decode().rstrip("=")
        assert decode_jwt_payload(f"header.{body}.signature") is None


class TestTokenClaims:
    def test_reads_the_access_token_claims(self):
        cached = {"access_token": _jwt({"sub": "someone"})}
        assert token_claims(cached) == {"sub": "someone"}

    @pytest.mark.parametrize(
        "cached",
        [None, {}, {"access_token": None}, {"access_token": 123}, {"access_token": "opaque"}],
    )
    def test_returns_none_when_there_are_no_readable_claims(self, cached):
        assert token_claims(cached) is None


class TestDescribeIdentity:
    def test_reports_the_subject(self):
        """``sub`` is a login name, so it displays with no API lookup and no ``openid`` scope."""
        assert describe_identity({"access_token": _jwt({"sub": "leonardoschwarz"})}) == "leonardoschwarz"

    @pytest.mark.parametrize(
        "cached",
        [
            None,
            {"access_token": "opaque-token-from-an-older-server"},
            {"access_token": _jwt({"scope": "api:read"})},
            {"access_token": _jwt({"sub": "  "})},
            {"access_token": _jwt({"sub": 42})},
        ],
    )
    def test_degrades_to_unknown_rather_than_raising(self, cached):
        assert describe_identity(cached) == UNKNOWN_IDENTITY


class TestGrantedScope:
    def test_prefers_the_cache_entry(self):
        cached = {"scope": "api:write", "access_token": _jwt({"scope": "api:read"})}
        assert granted_scope(cached) == "api:write"

    def test_falls_back_to_the_token_claim(self):
        assert granted_scope({"access_token": _jwt({"scope": "api:read tus"})}) == "api:read tus"

    @pytest.mark.parametrize(
        "cached",
        [None, {}, {"scope": "   "}, {"access_token": "opaque"}, {"access_token": _jwt({"sub": "someone"})}],
    )
    def test_returns_none_when_no_scope_is_recorded(self, cached):
        assert granted_scope(cached) is None

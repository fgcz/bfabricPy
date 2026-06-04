from __future__ import annotations

import hashlib
import base64
import threading
from unittest.mock import MagicMock, patch

import httpx
import pytest

from bfabric.errors import BfabricOAuthError
from bfabric._oauth.pkce import (
    _AuthorizationResult,
    _CallbackServer,
    _exchange_code,
    _generate_challenge,
    _generate_verifier,
    pkce_login,
)


class TestGenerateVerifier:
    def test_default_length(self):
        verifier = _generate_verifier()
        assert len(verifier) == 128

    def test_custom_length(self):
        verifier = _generate_verifier(length=43)
        assert len(verifier) == 43

    def test_url_safe_chars(self):
        verifier = _generate_verifier()
        # URL-safe base64 alphabet: A-Z, a-z, 0-9, -, _
        for char in verifier:
            assert char.isalnum() or char in ("-", "_")

    def test_randomness(self):
        v1 = _generate_verifier()
        v2 = _generate_verifier()
        assert v1 != v2

    def test_rejects_length_below_43(self):
        with pytest.raises(ValueError, match="43..128"):
            _generate_verifier(length=42)

    def test_rejects_length_above_128(self):
        with pytest.raises(ValueError, match="43..128"):
            _generate_verifier(length=129)


class TestGenerateChallenge:
    def test_known_vector(self):
        # RFC 7636 Appendix B test vector
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
        expected = base64.urlsafe_b64encode(expected_digest).rstrip(b"=").decode("ascii")
        assert _generate_challenge(verifier) == expected

    def test_no_padding(self):
        challenge = _generate_challenge("test_verifier_string")
        assert "=" not in challenge

    def test_deterministic(self):
        verifier = "some_fixed_verifier"
        assert _generate_challenge(verifier) == _generate_challenge(verifier)


class TestCallbackServer:
    def test_redirect_uri_format(self):
        server = _CallbackServer(port=0)
        port = server.server_address[1]
        assert server.redirect_uri == f"http://127.0.0.1:{port}/callback"
        server.server_close()

    def test_captures_code_and_state(self):
        server = _CallbackServer(port=0)
        port = server.server_address[1]

        # Simulate the OAuth callback in a thread
        def make_request():
            response = httpx.get(
                f"http://127.0.0.1:{port}/callback?code=auth_code_123&state=csrf_state_456"
            )
            assert response.status_code == 200

        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        make_request()
        server_thread.join(timeout=5)

        assert server.result.code == "auth_code_123"
        assert server.result.state == "csrf_state_456"
        assert server.result.error is None
        server.server_close()

    def test_captures_error(self):
        server = _CallbackServer(port=0)
        port = server.server_address[1]

        def make_request():
            httpx.get(
                f"http://127.0.0.1:{port}/callback?error=access_denied&error_description=User+denied"
            )

        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        make_request()
        server_thread.join(timeout=5)

        assert server.result.error == "access_denied"
        assert server.result.error_description == "User denied"
        assert server.result.code is None
        server.server_close()


class TestExchangeCode:
    def test_posts_correct_params(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "at", "refresh_token": "rt"}

        with patch("bfabric._oauth.pkce.httpx.post", return_value=mock_response) as mock_post:
            result = _exchange_code(
                token_url="https://example.com/rest/oauth/token",
                client_id="my-client",
                code="auth_code",
                redirect_uri="http://127.0.0.1:12345/callback",
                code_verifier="my_verifier",
            )

        mock_post.assert_called_once_with(
            "https://example.com/rest/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": "my-client",
                "code": "auth_code",
                "redirect_uri": "http://127.0.0.1:12345/callback",
                "code_verifier": "my_verifier",
            },
            timeout=30,
        )
        assert result == {"access_token": "at", "refresh_token": "rt"}

    def test_raises_on_http_error(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=MagicMock()
        )

        with patch("bfabric._oauth.pkce.httpx.post", return_value=mock_response):
            with pytest.raises(httpx.HTTPStatusError):
                _exchange_code(
                    token_url="https://example.com/rest/oauth/token",
                    client_id="id",
                    code="code",
                    redirect_uri="http://127.0.0.1:8000/callback",
                    code_verifier="verifier",
                )


class TestPkceLogin:
    def test_happy_path(self):
        token_dict = {"access_token": "jwt_here", "refresh_token": "rt_here"}

        with (
            patch("bfabric._oauth.pkce._CallbackServer") as mock_server_cls,
            patch("bfabric._oauth.pkce._exchange_code", return_value=token_dict) as mock_exchange,
            patch("bfabric._oauth.pkce.webbrowser.open", return_value=True),
            patch("bfabric._oauth.pkce.secrets.token_urlsafe", return_value="fixed_state"),
            patch("bfabric._oauth.pkce._generate_verifier", return_value="fixed_verifier"),
            patch("bfabric._oauth.pkce._generate_challenge", return_value="fixed_challenge"),
        ):
            mock_server = MagicMock()
            mock_server.redirect_uri = "http://127.0.0.1:9999/callback"
            mock_server.result = _AuthorizationResult(
                code="the_code", state="fixed_state"
            )
            mock_server.serve_forever = MagicMock()
            mock_server_cls.return_value = mock_server

            result = pkce_login("https://example.com/bfabric", client_id="test-cli")

        assert result == token_dict
        mock_exchange.assert_called_once_with(
            token_url="https://example.com/bfabric/rest/oauth/token",
            client_id="test-cli",
            code="the_code",
            redirect_uri="http://127.0.0.1:9999/callback",
            code_verifier="fixed_verifier",
        )

    def test_state_mismatch_raises(self):
        with (
            patch("bfabric._oauth.pkce._CallbackServer") as mock_server_cls,
            patch("bfabric._oauth.pkce.webbrowser.open", return_value=True),
            patch("bfabric._oauth.pkce.secrets.token_urlsafe", return_value="expected_state"),
            patch("bfabric._oauth.pkce._generate_verifier", return_value="v"),
            patch("bfabric._oauth.pkce._generate_challenge", return_value="c"),
        ):
            mock_server = MagicMock()
            mock_server.redirect_uri = "http://127.0.0.1:9999/callback"
            mock_server.result = _AuthorizationResult(
                code="code", state="wrong_state"
            )
            mock_server.serve_forever = MagicMock()
            mock_server_cls.return_value = mock_server

            with pytest.raises(BfabricOAuthError, match="CSRF state mismatch") as exc_info:
                pkce_login("https://example.com/bfabric")
            # State values must NOT appear in the error message (security)
            assert "expected_state" not in str(exc_info.value)
            assert "wrong_state" not in str(exc_info.value)

    def test_error_from_server_raises(self):
        with (
            patch("bfabric._oauth.pkce._CallbackServer") as mock_server_cls,
            patch("bfabric._oauth.pkce.webbrowser.open", return_value=True),
            patch("bfabric._oauth.pkce.secrets.token_urlsafe", return_value="state"),
            patch("bfabric._oauth.pkce._generate_verifier", return_value="v"),
            patch("bfabric._oauth.pkce._generate_challenge", return_value="c"),
        ):
            mock_server = MagicMock()
            mock_server.redirect_uri = "http://127.0.0.1:9999/callback"
            mock_server.result = _AuthorizationResult(
                error="access_denied",
                error_description="User denied the request",
                state="state",
            )
            mock_server.serve_forever = MagicMock()
            mock_server_cls.return_value = mock_server

            with pytest.raises(RuntimeError, match="Authorization error: access_denied"):
                pkce_login("https://example.com/bfabric")

    def test_timeout_raises(self):
        with (
            patch("bfabric._oauth.pkce._CallbackServer") as mock_server_cls,
            patch("bfabric._oauth.pkce.webbrowser.open", return_value=True),
            patch("bfabric._oauth.pkce.secrets.token_urlsafe", return_value="state"),
            patch("bfabric._oauth.pkce._generate_verifier", return_value="v"),
            patch("bfabric._oauth.pkce._generate_challenge", return_value="c"),
            patch("bfabric._oauth.pkce.threading.Thread") as mock_thread_cls,
        ):
            mock_server = MagicMock()
            mock_server.redirect_uri = "http://127.0.0.1:9999/callback"
            mock_server_cls.return_value = mock_server

            mock_thread = MagicMock()
            mock_thread.is_alive.return_value = True
            mock_thread_cls.return_value = mock_thread

            with pytest.raises(RuntimeError, match="timed out"):
                pkce_login("https://example.com/bfabric", timeout=0.1)

    def test_browser_fallback_prints_url(self, capsys):
        with (
            patch("bfabric._oauth.pkce._CallbackServer") as mock_server_cls,
            patch("bfabric._oauth.pkce._exchange_code", return_value={"access_token": "t"}),
            patch("bfabric._oauth.pkce.webbrowser.open", return_value=False),
            patch("bfabric._oauth.pkce.secrets.token_urlsafe", return_value="state"),
            patch("bfabric._oauth.pkce._generate_verifier", return_value="v"),
            patch("bfabric._oauth.pkce._generate_challenge", return_value="c"),
        ):
            mock_server = MagicMock()
            mock_server.redirect_uri = "http://127.0.0.1:9999/callback"
            mock_server.result = _AuthorizationResult(code="code", state="state")
            mock_server.serve_forever = MagicMock()
            mock_server_cls.return_value = mock_server

            pkce_login("https://example.com/bfabric")

        captured = capsys.readouterr()
        assert "Open this URL to log in:" in captured.err
        assert "https://example.com/bfabric/rest/oauth/authorize" in captured.err

    def test_open_browser_false_prints_url(self, capsys):
        with (
            patch("bfabric._oauth.pkce._CallbackServer") as mock_server_cls,
            patch("bfabric._oauth.pkce._exchange_code", return_value={"access_token": "t"}),
            patch("bfabric._oauth.pkce.secrets.token_urlsafe", return_value="state"),
            patch("bfabric._oauth.pkce._generate_verifier", return_value="v"),
            patch("bfabric._oauth.pkce._generate_challenge", return_value="c"),
        ):
            mock_server = MagicMock()
            mock_server.redirect_uri = "http://127.0.0.1:9999/callback"
            mock_server.result = _AuthorizationResult(code="code", state="state")
            mock_server.serve_forever = MagicMock()
            mock_server_cls.return_value = mock_server

            pkce_login("https://example.com/bfabric", open_browser=False)

        captured = capsys.readouterr()
        assert "Open this URL to log in:" in captured.err

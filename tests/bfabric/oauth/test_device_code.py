from __future__ import annotations

import httpx
import pytest

from bfabric._oauth.device_code import (
    _poll_for_token,
    _request_device_code,
    device_code_login,
)


class TestRequestDeviceCode:
    def test_posts_correct_params(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.json.return_value = {
            "device_code": "dc_123",
            "user_code": "ABCD-1234",
            "verification_uri": "https://example.com/device",
            "interval": 5,
            "expires_in": 600,
        }

        mock_post = mocker.patch("bfabric._oauth.device_code.httpx.post", return_value=mock_response)
        result = _request_device_code(
            "https://example.com/bfabric",
            client_id="test-cli",
            scope="api:read api:write",
        )

        mock_post.assert_called_once_with(
            "https://example.com/bfabric/rest/oauth/device_authorization",
            data={
                "client_id": "test-cli",
                "scope": "api:read api:write",
            },
            timeout=30,
        )
        assert result == mock_response.json.return_value

    def test_raises_on_http_error(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=mocker.MagicMock(), response=mocker.MagicMock()
        )

        mocker.patch("bfabric._oauth.device_code.httpx.post", return_value=mock_response)
        with pytest.raises(httpx.HTTPStatusError):
            _request_device_code(
                "https://example.com/bfabric",
                client_id="id",
                scope="api:read",
            )


class TestPollForToken:
    def test_success_on_first_poll(self, mocker):
        token_dict = {"access_token": "at", "refresh_token": "rt"}
        mock_response = mocker.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = token_dict

        mock_post = mocker.patch("bfabric._oauth.device_code.httpx.post", return_value=mock_response)
        result = _poll_for_token(
            "https://example.com/bfabric",
            device_code="dc_123",
            client_id="test-cli",
            interval=5,
            timeout=60,
        )

        assert result == token_dict
        mock_post.assert_called_once_with(
            "https://example.com/bfabric/rest/oauth/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": "dc_123",
                "client_id": "test-cli",
            },
            timeout=30,
        )

    def test_authorization_pending_then_success(self, mocker):
        pending_response = mocker.MagicMock()
        pending_response.status_code = 400
        pending_response.json.return_value = {"error": "authorization_pending"}

        success_response = mocker.MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"access_token": "at"}

        mocker.patch("bfabric._oauth.device_code.httpx.post", side_effect=[pending_response, success_response])
        mock_sleep = mocker.patch("bfabric._oauth.device_code.time.sleep")
        result = _poll_for_token(
            "https://example.com/bfabric",
            device_code="dc_123",
            client_id="test-cli",
            interval=5,
            timeout=60,
        )

        assert result == {"access_token": "at"}
        mock_sleep.assert_called_once_with(5)

    def test_slow_down_increases_interval(self, mocker):
        slow_down_response = mocker.MagicMock()
        slow_down_response.status_code = 400
        slow_down_response.json.return_value = {"error": "slow_down"}

        success_response = mocker.MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"access_token": "at"}

        mocker.patch("bfabric._oauth.device_code.httpx.post", side_effect=[slow_down_response, success_response])
        mock_sleep = mocker.patch("bfabric._oauth.device_code.time.sleep")
        result = _poll_for_token(
            "https://example.com/bfabric",
            device_code="dc_123",
            client_id="test-cli",
            interval=5,
            timeout=60,
        )

        assert result == {"access_token": "at"}
        # interval should have been increased by 5 (5 -> 10)
        mock_sleep.assert_called_once_with(10)

    def test_access_denied_raises(self, mocker):
        denied_response = mocker.MagicMock()
        denied_response.status_code = 400
        denied_response.json.return_value = {"error": "access_denied"}

        mocker.patch("bfabric._oauth.device_code.httpx.post", return_value=denied_response)
        with pytest.raises(RuntimeError, match="User denied the authorization request"):
            _poll_for_token(
                "https://example.com/bfabric",
                device_code="dc_123",
                client_id="test-cli",
                interval=5,
                timeout=60,
            )

    def test_expired_token_raises(self, mocker):
        expired_response = mocker.MagicMock()
        expired_response.status_code = 400
        expired_response.json.return_value = {"error": "expired_token"}

        mocker.patch("bfabric._oauth.device_code.httpx.post", return_value=expired_response)
        with pytest.raises(RuntimeError, match="Device code expired"):
            _poll_for_token(
                "https://example.com/bfabric",
                device_code="dc_123",
                client_id="test-cli",
                interval=5,
                timeout=60,
            )

    def test_timeout_raises(self, mocker):
        pending_response = mocker.MagicMock()
        pending_response.status_code = 400
        pending_response.json.return_value = {"error": "authorization_pending"}

        mocker.patch("bfabric._oauth.device_code.httpx.post", return_value=pending_response)
        mocker.patch("bfabric._oauth.device_code.time.monotonic", side_effect=[0, 100])
        mocker.patch("bfabric._oauth.device_code.time.sleep")
        with pytest.raises(RuntimeError, match="timed out"):
            _poll_for_token(
                "https://example.com/bfabric",
                device_code="dc_123",
                client_id="test-cli",
                interval=5,
                timeout=60,
            )

    def test_retries_on_server_error(self, mocker):
        error_response = mocker.MagicMock()
        error_response.status_code = 503

        success_response = mocker.MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"access_token": "at"}

        mocker.patch("bfabric._oauth.device_code.httpx.post", side_effect=[error_response, success_response])
        mock_sleep = mocker.patch("bfabric._oauth.device_code.time.sleep")
        result = _poll_for_token(
            "https://example.com/bfabric",
            device_code="dc_123",
            client_id="test-cli",
            interval=5,
            timeout=60,
        )

        assert result == {"access_token": "at"}
        mock_sleep.assert_called_once_with(5)

    def test_retries_on_transport_error(self, mocker):
        success_response = mocker.MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"access_token": "at"}

        mocker.patch(
            "bfabric._oauth.device_code.httpx.post",
            side_effect=[httpx.ConnectError("connection refused"), success_response],
        )
        mock_sleep = mocker.patch("bfabric._oauth.device_code.time.sleep")
        result = _poll_for_token(
            "https://example.com/bfabric",
            device_code="dc_123",
            client_id="test-cli",
            interval=5,
            timeout=60,
        )

        assert result == {"access_token": "at"}
        mock_sleep.assert_called_once_with(5)

    def test_unknown_error_raises_with_description(self, mocker):
        error_response = mocker.MagicMock()
        error_response.status_code = 400
        error_response.json.return_value = {
            "error": "server_error",
            "error_description": "Internal failure",
        }

        mocker.patch("bfabric._oauth.device_code.httpx.post", return_value=error_response)
        with pytest.raises(RuntimeError, match="Device code token error: server_error .* Internal failure"):
            _poll_for_token(
                "https://example.com/bfabric",
                device_code="dc_123",
                client_id="test-cli",
                interval=5,
                timeout=60,
            )


class TestDeviceCodeLogin:
    def test_happy_path(self, mocker, capsys):
        device_response = {
            "device_code": "dc_456",
            "user_code": "WXYZ-9876",
            "verification_uri": "https://example.com/device",
            "interval": 5,
            "expires_in": 600,
        }
        token_dict = {"access_token": "jwt_here", "refresh_token": "rt_here"}

        mock_request = mocker.patch(
            "bfabric._oauth.device_code._request_device_code",
            return_value=device_response,
        )
        mock_poll = mocker.patch(
            "bfabric._oauth.device_code._poll_for_token",
            return_value=token_dict,
        )
        result = device_code_login(
            "https://example.com/bfabric",
            client_id="test-cli",
            scope="api:read api:write",
            timeout=300.0,
        )

        assert result == token_dict
        mock_request.assert_called_once_with(
            "https://example.com/bfabric",
            client_id="test-cli",
            scope="api:read api:write",
        )
        mock_poll.assert_called_once_with(
            "https://example.com/bfabric",
            device_code="dc_456",
            client_id="test-cli",
            interval=5.0,
            timeout=300.0,
        )

        captured = capsys.readouterr()
        assert "WXYZ-9876" in captured.err
        assert "https://example.com/device" in captured.err

    def test_prints_verification_uri_complete(self, mocker, capsys):
        device_response = {
            "device_code": "dc_456",
            "user_code": "WXYZ-9876",
            "verification_uri": "https://example.com/device",
            "verification_uri_complete": "https://example.com/device?user_code=WXYZ-9876",
            "interval": 5,
            "expires_in": 600,
        }

        mocker.patch("bfabric._oauth.device_code._request_device_code", return_value=device_response)
        mocker.patch("bfabric._oauth.device_code._poll_for_token", return_value={"access_token": "at"})
        device_code_login("https://example.com/bfabric")

        captured = capsys.readouterr()
        assert "https://example.com/device?user_code=WXYZ-9876" in captured.err

    def test_strips_trailing_slash(self, mocker):
        device_response = {
            "device_code": "dc_456",
            "user_code": "CODE",
            "verification_uri": "https://example.com/device",
            "interval": 5,
        }

        mock_request = mocker.patch(
            "bfabric._oauth.device_code._request_device_code",
            return_value=device_response,
        )
        mock_poll = mocker.patch(
            "bfabric._oauth.device_code._poll_for_token",
            return_value={"access_token": "at"},
        )
        device_code_login("https://example.com/bfabric///")

        mock_request.assert_called_once_with(
            "https://example.com/bfabric",
            client_id="bfabric-cli",
            scope="api:read api:write",
        )
        assert mock_poll.call_args[0][0] == "https://example.com/bfabric"

    def test_default_interval_when_missing(self, mocker):
        device_response = {
            "device_code": "dc_456",
            "user_code": "CODE",
            "verification_uri": "https://example.com/device",
        }

        mocker.patch("bfabric._oauth.device_code._request_device_code", return_value=device_response)
        mock_poll = mocker.patch(
            "bfabric._oauth.device_code._poll_for_token",
            return_value={"access_token": "at"},
        )
        device_code_login("https://example.com/bfabric")

        assert mock_poll.call_args[1]["interval"] == 5.0

"""Tests for `is_employee` and the `/user/is_employee` endpoint."""

from __future__ import annotations

import pytest
from bfabric import BfabricAuth
from bfabric._oauth.url_token import UrlTokenContext
from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric.entities import User
from pydantic import SecretStr

from bfabric_rest_proxy.feeder_operations.is_employee import is_employee

INSTANCE = "https://test.bfabric.example.com/"


def _user(login: str = "test_user", **fields: object) -> User:
    return User(
        data_dict={"classname": "user", "id": 1, "login": login, **fields},
        client=None,
        bfabric_instance=INSTANCE,
    )


@pytest.fixture
def mock_find_by_login(mocker):
    return mocker.patch("bfabric_rest_proxy.feeder_operations.is_employee.User.find_by_login")


class TestIsEmployee:
    """Unit tests for the pure `is_employee` helper."""

    def test_empdegree_missing_returns_false(
        self, mock_bfabric_user_client, mock_bfabric_feeder_client, mock_find_by_login
    ):
        mock_find_by_login.return_value = _user()
        assert is_employee(user_client=mock_bfabric_user_client, feeder_client=mock_bfabric_feeder_client) is False

    def test_empdegree_none_returns_false(
        self, mock_bfabric_user_client, mock_bfabric_feeder_client, mock_find_by_login
    ):
        mock_find_by_login.return_value = _user(empdegree=None)
        assert is_employee(user_client=mock_bfabric_user_client, feeder_client=mock_bfabric_feeder_client) is False

    def test_empdegree_positive_integer_returns_true(
        self, mock_bfabric_user_client, mock_bfabric_feeder_client, mock_find_by_login
    ):
        mock_find_by_login.return_value = _user(empdegree="100")
        assert is_employee(user_client=mock_bfabric_user_client, feeder_client=mock_bfabric_feeder_client) is True

    def test_empdegree_zero_returns_false(
        self, mock_bfabric_user_client, mock_bfabric_feeder_client, mock_find_by_login
    ):
        mock_find_by_login.return_value = _user(empdegree="0")
        assert is_employee(user_client=mock_bfabric_user_client, feeder_client=mock_bfabric_feeder_client) is False

    def test_no_user_record_raises(self, mock_bfabric_user_client, mock_bfabric_feeder_client, mock_find_by_login):
        mock_find_by_login.return_value = None
        with pytest.raises(RuntimeError, match="User record not found"):
            is_employee(user_client=mock_bfabric_user_client, feeder_client=mock_bfabric_feeder_client)

    def test_looks_up_authenticated_login_via_feeder_client(
        self, mock_bfabric_user_client, mock_bfabric_feeder_client, mock_find_by_login
    ):
        mock_find_by_login.return_value = _user(empdegree="100")
        is_employee(user_client=mock_bfabric_user_client, feeder_client=mock_bfabric_feeder_client)
        mock_find_by_login.assert_called_once_with(login="test_user", client=mock_bfabric_feeder_client)

    def test_resolves_current_identity_subject_not_auth_login(
        self, mock_bfabric_user_client, mock_bfabric_feeder_client, mock_find_by_login
    ):
        # Under OAuth, auth.login is only the "__oauth__" sentinel; the real user is the
        # token subject. The lookup must follow the subject, not auth.login.
        mock_bfabric_user_client.auth = BfabricAuth(login=OAUTH_LOGIN, password=SecretStr("q" * 32))
        mock_bfabric_user_client.current_identity = UrlTokenContext(subject="real_user")
        mock_find_by_login.return_value = _user(login="real_user", empdegree="100")

        assert is_employee(user_client=mock_bfabric_user_client, feeder_client=mock_bfabric_feeder_client) is True
        mock_find_by_login.assert_called_once_with(login="real_user", client=mock_bfabric_feeder_client)

    def test_undeterminable_login_raises(
        self, mock_bfabric_user_client, mock_bfabric_feeder_client, mock_find_by_login
    ):
        mock_bfabric_user_client.current_identity = UrlTokenContext(subject=None)
        with pytest.raises(RuntimeError, match="Could not determine the authenticated user's login"):
            is_employee(user_client=mock_bfabric_user_client, feeder_client=mock_bfabric_feeder_client)
        mock_find_by_login.assert_not_called()


class TestUserIsEmployeeEndpoint:
    """Integration tests for POST /user/is_employee."""

    def test_employee_returns_true(self, client, mock_find_by_login):
        mock_find_by_login.return_value = _user(empdegree="100")

        response = client.post(
            "/user/is_employee",
            json={"login": "test_user", "webservicepassword": "y" * 32},
        )

        assert response.status_code == 200
        assert response.json() == {"is_employee": True}

    def test_non_employee_returns_false(self, client, mock_find_by_login):
        mock_find_by_login.return_value = _user(empdegree="0")

        response = client.post(
            "/user/is_employee",
            json={"login": "test_user", "webservicepassword": "y" * 32},
        )

        assert response.status_code == 200
        assert response.json() == {"is_employee": False}

    def test_missing_empdegree_returns_false(self, client, mock_find_by_login):
        mock_find_by_login.return_value = _user()

        response = client.post(
            "/user/is_employee",
            json={"login": "test_user", "webservicepassword": "y" * 32},
        )

        assert response.status_code == 200
        assert response.json() == {"is_employee": False}

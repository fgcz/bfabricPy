"""Tests for `is_employee` and the `/user/is_employee` endpoint."""

from __future__ import annotations

import pytest
from bfabric.entities import User

from bfabric_rest_proxy.user_operations.is_employee import is_employee

INSTANCE = "https://test.bfabric.example.com/"


def _user(login: str = "test_user", **fields: object) -> User:
    return User(
        data_dict={"classname": "user", "id": 1, "login": login, **fields},
        client=None,
        bfabric_instance=INSTANCE,
    )


class TestIsEmployee:
    """Unit tests for the pure `is_employee` helper."""

    def test_empdegree_missing_returns_false(self, mock_bfabric_user_client):
        mock_bfabric_user_client.reader.query_one.return_value = _user()
        assert is_employee(mock_bfabric_user_client) is False

    def test_empdegree_positive_integer_returns_true(self, mock_bfabric_user_client):
        mock_bfabric_user_client.reader.query_one.return_value = _user(empdegree="100")
        assert is_employee(mock_bfabric_user_client) is True

    def test_empdegree_zero_returns_false(self, mock_bfabric_user_client):
        mock_bfabric_user_client.reader.query_one.return_value = _user(empdegree="0")
        assert is_employee(mock_bfabric_user_client) is False

    def test_no_user_record_raises(self, mock_bfabric_user_client):
        mock_bfabric_user_client.reader.query_one.return_value = None
        with pytest.raises(RuntimeError, match="User record not found"):
            is_employee(mock_bfabric_user_client)

    def test_queries_user_endpoint_by_login(self, mock_bfabric_user_client):
        mock_bfabric_user_client.reader.query_one.return_value = _user(empdegree="100")
        is_employee(mock_bfabric_user_client)
        mock_bfabric_user_client.reader.query_one.assert_called_once_with(
            "user", {"login": "test_user"}, expected_type=User
        )


class TestUserIsEmployeeEndpoint:
    """Integration tests for POST /user/is_employee."""

    def test_employee_returns_true(self, client, mock_bfabric_user_client):
        mock_bfabric_user_client.reader.query_one.return_value = _user(empdegree="100")

        response = client.post(
            "/user/is_employee",
            json={"login": "test_user", "webservicepassword": "y" * 32},
        )

        assert response.status_code == 200
        assert response.json() == {"is_employee": True}

    def test_non_employee_returns_false(self, client, mock_bfabric_user_client):
        mock_bfabric_user_client.reader.query_one.return_value = _user()

        response = client.post(
            "/user/is_employee",
            json={"login": "test_user", "webservicepassword": "y" * 32},
        )

        assert response.status_code == 200
        assert response.json() == {"is_employee": False}

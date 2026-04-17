"""Tests for `_is_employee` helper and the `/user/is_employee` endpoint."""

from __future__ import annotations

import pytest
from bfabric.results.result_container import ResultContainer

from bfabric_rest_proxy.server import _is_employee


class TestIsEmployeeHelper:
    """Unit tests for the pure `_is_employee` function."""

    def test_empdegree_missing_returns_false(self, mock_bfabric_user_client):
        mock_bfabric_user_client.read.return_value = ResultContainer(
            [{"login": "test_user", "name": "Test User"}], total_pages_api=1, errors=[]
        )
        assert _is_employee(mock_bfabric_user_client) is False

    def test_empdegree_positive_integer_returns_true(self, mock_bfabric_user_client):
        mock_bfabric_user_client.read.return_value = ResultContainer(
            [{"login": "test_user", "empdegree": "100"}], total_pages_api=1, errors=[]
        )
        assert _is_employee(mock_bfabric_user_client) is True

    def test_empdegree_positive_fraction_returns_true(self, mock_bfabric_user_client):
        mock_bfabric_user_client.read.return_value = ResultContainer(
            [{"login": "test_user", "empdegree": "0.5"}], total_pages_api=1, errors=[]
        )
        assert _is_employee(mock_bfabric_user_client) is True

    def test_empdegree_zero_returns_false(self, mock_bfabric_user_client):
        mock_bfabric_user_client.read.return_value = ResultContainer(
            [{"login": "test_user", "empdegree": "0"}], total_pages_api=1, errors=[]
        )
        assert _is_employee(mock_bfabric_user_client) is False

    def test_empdegree_unparseable_returns_false(self, mock_bfabric_user_client):
        mock_bfabric_user_client.read.return_value = ResultContainer(
            [{"login": "test_user", "empdegree": ""}], total_pages_api=1, errors=[]
        )
        assert _is_employee(mock_bfabric_user_client) is False

    def test_empty_results_raises(self, mock_bfabric_user_client):
        mock_bfabric_user_client.read.return_value = ResultContainer([], total_pages_api=0, errors=[])
        with pytest.raises(RuntimeError, match="User record not found"):
            _is_employee(mock_bfabric_user_client)

    def test_queries_user_endpoint_by_login(self, mock_bfabric_user_client):
        mock_bfabric_user_client.read.return_value = ResultContainer(
            [{"login": "test_user", "empdegree": "100"}], total_pages_api=1, errors=[]
        )
        _is_employee(mock_bfabric_user_client)
        mock_bfabric_user_client.read.assert_called_once_with("user", {"login": "test_user"})


class TestUserIsEmployeeEndpoint:
    """Integration tests for POST /user/is_employee."""

    def test_employee_returns_true(self, client, mock_bfabric_user_client):
        mock_bfabric_user_client.read.return_value = ResultContainer(
            [{"login": "test_user", "empdegree": "100"}], total_pages_api=1, errors=[]
        )

        response = client.post(
            "/user/is_employee",
            json={"login": "test_user", "webservicepassword": "y" * 32},
        )

        assert response.status_code == 200
        assert response.json() == {"is_employee": True}

        call_args = mock_bfabric_user_client.read.call_args
        assert call_args.args[0] == "user"
        assert call_args.args[1] == {"login": "test_user"}

    def test_non_employee_returns_false(self, client, mock_bfabric_user_client):
        mock_bfabric_user_client.read.return_value = ResultContainer(
            [{"login": "test_user", "name": "Test User"}], total_pages_api=1, errors=[]
        )

        response = client.post(
            "/user/is_employee",
            json={"login": "test_user", "webservicepassword": "y" * 32},
        )

        assert response.status_code == 200
        assert response.json() == {"is_employee": False}

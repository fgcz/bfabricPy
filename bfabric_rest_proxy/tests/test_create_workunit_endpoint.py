"""Integration tests for /create/workunit/v1 endpoint.

This module tests the workunit creation endpoint with mocked Bfabric client
to ensure no real API calls are made during testing.
"""

import pytest
from bfabric import BfabricAuth
from bfabric._oauth.url_token import UrlTokenContext
from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric.results.result_container import ResultContainer
from pydantic import SecretStr

from bfabric_rest_proxy.feeder_operations.create_workunit import CreateWorkunitRequest, create_workunit


class TestCreateWorkunitEndpoint:
    """Tests for the /create/workunit/v1 endpoint."""

    def test_create_workunit_success(self, client, mock_bfabric_user_client, mock_bfabric_feeder_client, mocker):
        """Test successful workunit creation."""
        mock_workunit = mocker.MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test Workunit", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        mocker.patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit)

        response = client.post(
            "/create/workunit/v1",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                "params": {
                    "container_id": 100,
                    "application_id": 5,
                    "workunit_name": "Test Workunit",
                    "parameters": {"param1": "value1"},
                    "resources": {},
                    "links": {},
                },
            },
        )

        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 1

    def test_create_workunit_with_parameters(
        self, client, mock_bfabric_user_client, mock_bfabric_feeder_client, mocker
    ):
        """Test workunit creation with parameters."""
        mock_workunit = mocker.MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test with Params", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        mocker.patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit)

        response = client.post(
            "/create/workunit/v1",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                "params": {
                    "container_id": 100,
                    "application_id": 5,
                    "workunit_name": "Test with Params",
                    "parameters": {"param1": "value1", "param2": "value2"},
                    "resources": {},
                    "links": {},
                },
            },
        )

        assert response.status_code == 200, f"Response: {response.text}"

    def test_create_workunit_with_resources(self, client, mock_bfabric_user_client, mock_bfabric_feeder_client, mocker):
        """Test workunit creation with resources."""
        mock_workunit = mocker.MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test with Resources", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        mocker.patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit)

        response = client.post(
            "/create/workunit/v1",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                "params": {
                    "container_id": 100,
                    "application_id": 5,
                    "workunit_name": "Test with Resources",
                    "parameters": {},
                    "resources": {"resource1": "base64encodeddata"},
                    "links": {},
                },
            },
        )

        assert response.status_code == 200, f"Response: {response.text}"

    def test_create_workunit_with_links(self, client, mock_bfabric_user_client, mock_bfabric_feeder_client, mocker):
        """Test workunit creation with links."""
        mock_workunit = mocker.MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test with Links", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        mocker.patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit)

        response = client.post(
            "/create/workunit/v1",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                "params": {
                    "container_id": 100,
                    "application_id": 5,
                    "workunit_name": "Test with Links",
                    "parameters": {},
                    "resources": {},
                    "links": {"GitHub": "https://github.com/example"},
                },
            },
        )

        assert response.status_code == 200, f"Response: {response.text}"

    def test_create_workunit_container_access_denied(
        self, client, mock_bfabric_user_client, mock_bfabric_feeder_client
    ):
        """Test that workunit creation fails if user lacks container access."""
        mock_bfabric_user_client.read.return_value = ResultContainer([], total_pages_api=0, errors=[])

        with pytest.raises(RuntimeError, match="Container authorization failed"):
            client.post(
                "/create/workunit/v1",
                json={
                    "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                    "params": {
                        "container_id": 999,
                        "application_id": 5,
                        "workunit_name": "Test",
                        "parameters": {"p": "v"},
                        "resources": {},
                        "links": {},
                    },
                },
            )

        assert not mock_bfabric_feeder_client.save.called

    def test_create_workunit_missing_required_fields(self, client):
        """Test that missing required fields are rejected."""
        response = client.post(
            "/create/workunit/v1",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                "params": {},
            },
        )

        assert response.status_code == 422

    def test_create_workunit_uses_both_clients(
        self, client, mock_bfabric_user_client, mock_bfabric_feeder_client, mocker
    ):
        """Test that workunit creation passes both user and feeder clients."""
        mock_workunit = mocker.MagicMock()
        mock_workunit.data_dict = {"id": 1, "name": "Test", "_entityclass": "workunit"}
        mock_workunit.uri = "https://test.bfabric.example.com/workunit/1"

        mock_create = mocker.patch("bfabric_rest_proxy.server.create_workunit", return_value=mock_workunit)

        client.post(
            "/create/workunit/v1",
            json={
                "auth": {"login": "test_user", "webservicepassword": "y" * 32},
                "params": {
                    "container_id": 100,
                    "application_id": 5,
                    "workunit_name": "Test",
                    "parameters": {"p": "v"},
                    "resources": {},
                    "links": {},
                },
            },
        )

        assert mock_create.called
        assert mock_create.call_args[1]["user_client"] == mock_bfabric_user_client
        assert mock_create.call_args[1]["feeder_client"] == mock_bfabric_feeder_client


class TestCreateWorkunitAuditAttributes:
    """Unit tests for the `create_workunit` wrapper's audit stamping."""

    @staticmethod
    def _request(**overrides):
        base = dict(
            container_id=100,
            application_id=5,
            workunit_name="Test",
            parameters={"p": "v"},
            resources={},
            links={},
        )
        base.update(overrides)
        return CreateWorkunitRequest(**base)

    def test_created_for_uses_current_identity_subject(
        self, mock_bfabric_user_client, mock_bfabric_feeder_client, mocker
    ):
        # Under OAuth, auth.login is only the "__oauth__" sentinel; "Created For" must name the
        # real user from current_identity.subject.
        mock_bfabric_user_client.auth = BfabricAuth(login=OAUTH_LOGIN, password=SecretStr("q" * 32))
        mock_bfabric_user_client.current_identity = UrlTokenContext(subject="real_user")
        mock_bfabric_user_client.read.return_value = ResultContainer([{"id": 100}], total_pages_api=1, errors=[])
        mock_create = mocker.patch("bfabric_rest_proxy.feeder_operations.create_workunit._create_workunit")

        create_workunit(
            user_client=mock_bfabric_user_client,
            feeder_client=mock_bfabric_feeder_client,
            request=self._request(),
        )

        assert mock_create.call_args.kwargs["audit_attributes"] == {"Created For": "real_user"}

    def test_created_using_recorded_alongside_created_for(
        self, mock_bfabric_user_client, mock_bfabric_feeder_client, mocker
    ):
        mock_bfabric_user_client.read.return_value = ResultContainer([{"id": 100}], total_pages_api=1, errors=[])
        mock_create = mocker.patch("bfabric_rest_proxy.feeder_operations.create_workunit._create_workunit")

        create_workunit(
            user_client=mock_bfabric_user_client,
            feeder_client=mock_bfabric_feeder_client,
            request=self._request(created_using="my-app/1.0"),
        )

        assert mock_create.call_args.kwargs["audit_attributes"] == {
            "Created For": "test_user",
            "Created Using": "my-app/1.0",
        }

    def test_undeterminable_login_raises(self, mock_bfabric_user_client, mock_bfabric_feeder_client, mocker):
        mock_bfabric_user_client.current_identity = UrlTokenContext(subject=None)
        mock_bfabric_user_client.read.return_value = ResultContainer([{"id": 100}], total_pages_api=1, errors=[])
        mock_create = mocker.patch("bfabric_rest_proxy.feeder_operations.create_workunit._create_workunit")

        with pytest.raises(RuntimeError, match="Could not determine the authenticated user's login"):
            create_workunit(
                user_client=mock_bfabric_user_client,
                feeder_client=mock_bfabric_feeder_client,
                request=self._request(),
            )
        mock_create.assert_not_called()

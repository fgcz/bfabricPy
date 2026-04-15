"""Unit tests for BfabricUser."""

from __future__ import annotations

import pytest
from bfabric import Bfabric

from bfabric_asgi_auth.session_data import SessionData
from bfabric_asgi_auth.user import BfabricUser


@pytest.fixture
def session_data() -> SessionData:
    return SessionData(
        bfabric_instance="https://fgcz-bfabric.uzh.ch/bfabric/",
        bfabric_auth_login="testuser",
        bfabric_auth_password="a" * 32,
    )


@pytest.fixture
def user(session_data: SessionData) -> BfabricUser:
    return BfabricUser(session_data)


class TestBfabricUser:
    def test_is_authenticated(self, user: BfabricUser) -> None:
        assert user.is_authenticated is True

    def test_login(self, user: BfabricUser) -> None:
        assert user.login == "testuser"

    def test_instance(self, user: BfabricUser) -> None:
        assert user.instance == "https://fgcz-bfabric.uzh.ch/bfabric/"

    def test_display_name(self, user: BfabricUser) -> None:
        assert user.display_name == "testuser"

    def test_identity(self, user: BfabricUser) -> None:
        assert user.identity == "testuser@https://fgcz-bfabric.uzh.ch/bfabric/"

    def test_get_bfabric_client(self, user: BfabricUser) -> None:
        client = user.get_bfabric_client()
        assert isinstance(client, Bfabric)
        assert client.auth.login == "testuser"
        assert client.auth.password.get_secret_value() == "a" * 32
        assert str(client.config.base_url) == "https://fgcz-bfabric.uzh.ch/bfabric/"

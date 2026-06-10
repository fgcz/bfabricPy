from pathlib import Path

import pytest

from bfabric.config import BfabricAuth
from bfabric.config.bfabric_auth import OAUTH_LOGIN


@pytest.fixture
def example_config_path() -> Path:
    return Path(__file__).parent / "example_config.yml"


def test_bfabric_auth_repr() -> None:
    assert (
        repr(BfabricAuth(login="login", password="x" * 32))
        == "BfabricAuth(login='login', password=SecretStr('**********'))"
    )


def test_bfabric_auth_str() -> None:
    assert str(BfabricAuth(login="login", password="x" * 32)) == "login='login' password=SecretStr('**********')"


class TestPasswordValidation:
    def test_non_oauth_accepts_32_chars(self) -> None:
        auth = BfabricAuth(login="user", password="x" * 32)
        assert auth.login == "user"
        assert auth.password.get_secret_value() == "x" * 32

    def test_non_oauth_rejects_short_password(self) -> None:
        with pytest.raises(ValueError, match="Password must be exactly 32 characters"):
            BfabricAuth(login="user", password="short")

    def test_non_oauth_rejects_long_password(self) -> None:
        with pytest.raises(ValueError, match="Password must be exactly 32 characters"):
            BfabricAuth(login="user", password="x" * 100)

    def test_oauth_accepts_long_jwt(self) -> None:
        jwt = "eyJhbGciOiJSUzI1NiJ9." + "x" * 500
        auth = BfabricAuth(login=OAUTH_LOGIN, password=jwt)
        assert auth.login == OAUTH_LOGIN
        assert auth.password.get_secret_value() == jwt

    def test_oauth_accepts_short_token(self) -> None:
        auth = BfabricAuth(login=OAUTH_LOGIN, password="tok")
        assert auth.password.get_secret_value() == "tok"

    def test_empty_password_rejected(self) -> None:
        with pytest.raises(ValueError):
            BfabricAuth(login="user", password="")

    def test_oauth_empty_password_rejected(self) -> None:
        with pytest.raises(ValueError):
            BfabricAuth(login=OAUTH_LOGIN, password="")


if __name__ == "__main__":
    pytest.main()

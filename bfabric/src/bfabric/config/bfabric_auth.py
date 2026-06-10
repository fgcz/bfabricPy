from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, SecretStr, model_validator

OAUTH_LOGIN = "__oauth__"


class BfabricAuth(BaseModel):
    """Holds the authentication data for the B-Fabric client."""

    login: Annotated[str, Field(min_length=1)]
    password: Annotated[SecretStr, Field(min_length=1)]

    @model_validator(mode="after")
    def _validate_password_length(self) -> BfabricAuth:
        """Enforce 32-char password constraint for non-OAuth logins.

        When login is ``__oauth__``, the password is a JWT and can be any length.
        For traditional logins, the password must be exactly 32 characters.
        """
        if self.login != OAUTH_LOGIN and len(self.password.get_secret_value()) != 32:
            raise ValueError("Password must be exactly 32 characters for non-OAuth logins")
        return self

"""Guards the config-file backward-compatibility contract.

The CLI must never write into a shared ``~/.bfabricpy.yml`` any environment that an
unmodified <=1.19.0 client cannot parse. Because the 1.19.0 ``ConfigFile`` validates *every*
environment eagerly and its ``BfabricAuth`` requires the password to be exactly 32 characters,
a single environment that pairs a ``login`` with a non-32-char secret poisons the *whole* file
for old clients. These tests vendor a minimal clone of the 1.19.0 schema and assert that the
current PAT-env shape stays parseable by it, while the old (rc1) inline-password shape does not.
"""

from __future__ import annotations

from typing import Annotated, Any

import pytest
from pydantic import BaseModel, Field, SecretStr, ValidationError, model_validator

from bfabric.config.config_file import EnvironmentConfig


# --- Vendored replica of the bfabric 1.19.0 config schema (do not "fix" to match new code) ---


class LegacyBfabricAuth(BaseModel):
    login: Annotated[str, Field(min_length=1)]
    password: Annotated[SecretStr, Field(min_length=32, max_length=32)]


class LegacyClientConfig(BaseModel):
    # 1.19.0 required a valid base_url and silently ignored unknown keys (pydantic default).
    base_url: str


class LegacyEnvironmentConfig(BaseModel):
    config: LegacyClientConfig
    auth: LegacyBfabricAuth | None = None

    @model_validator(mode="before")
    @classmethod
    def gather_config(cls, values: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(values, dict):
            return values
        values["config"] = {k: v for k, v in values.items() if k not in ["login", "password"]}
        return values

    @model_validator(mode="before")
    @classmethod
    def gather_auth(cls, values: dict[str, Any]) -> dict[str, Any]:
        if isinstance(values, dict) and "login" in values:
            values["auth"] = LegacyBfabricAuth.model_validate(values)
        return values


class LegacyConfigFile(BaseModel):
    general: Annotated[dict, Field(alias="GENERAL")]
    environments: dict[str, LegacyEnvironmentConfig]

    @model_validator(mode="before")
    @classmethod
    def gather_configs(cls, values: dict[str, Any]) -> dict[str, Any]:
        values["environments"] = {k: v for k, v in values.items() if k != "GENERAL"}
        return values


# --- Tests ---


def _pat_env_shape() -> dict[str, str]:
    """The environment dict the current ``login pat`` writer emits."""
    return {"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "short-pat-token"}


def test_pat_env_is_parseable_by_legacy_client():
    """A file with a current-shape PAT env plus a normal password env loads on a 1.19.0 client."""
    config = {
        "GENERAL": {"default_config": "PROD"},
        "PROD": {"base_url": "https://prod.example.com", "login": "user", "password": "x" * 32},
        "OAUTH": _pat_env_shape(),
    }
    legacy = LegacyConfigFile.model_validate(config)
    # The unrelated password env is still fully readable...
    assert legacy.environments["PROD"].auth.login == "user"
    # ...and the PAT env parses (old client just can't authenticate with it -> auth is None).
    assert legacy.environments["OAUTH"].auth is None
    assert legacy.environments["OAUTH"].config.base_url == "https://example.com/bfabric"


def test_legacy_client_rejects_old_rc1_pat_shape():
    """Negative control: the rc1 shape (login + inline short password) DID poison the file."""
    config = {
        "GENERAL": {"default_config": "PROD"},
        "PROD": {"base_url": "https://prod.example.com", "login": "user", "password": "x" * 32},
        "OAUTH": {"base_url": "https://example.com/bfabric", "login": "__oauth__", "password": "short-pat-token"},
    }
    with pytest.raises(ValidationError):
        LegacyConfigFile.model_validate(config)


def test_current_reader_parses_pat_env_shape():
    """Sanity check that the new reader understands the same shape the writer emits."""
    env = EnvironmentConfig.model_validate(_pat_env_shape())
    assert env.auth_method == "pat"
    assert env.auth.login == "__oauth__"
    assert env.auth.password.get_secret_value() == "short-pat-token"

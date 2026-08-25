"""In-memory representation of how a config environment authenticates.

The on-disk YAML is flat (``auth_method`` plus sibling keys); :func:`auth_method_from_flat` is the
only place it is interpreted. Writing goes the other way round: the CLI hands
:func:`bfabric.config.config_writer.write_environment_to_config` the flat keys directly, so these
models are parse-only and never serialise themselves back.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, ClassVar, Literal, get_args, override

from loguru import logger
from pydantic import BaseModel, Field, SecretStr

from bfabric.config.bfabric_auth import OAUTH_LOGIN, BfabricAuth

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bfabric.config.base_url import BaseUrl

    from bfabric.oauth._credential_provider import OAuthCredentialProvider


AuthMethodName = Literal["password", "oauth", "pat", "client_credentials"]
"""The ``auth_method`` values this version understands."""


class AuthMethodBase(BaseModel):
    """Base for the auth-method variants."""

    owned_keys: ClassVar[frozenset[str]] = frozenset()

    declared_name: AuthMethodName | None = None
    """The ``auth_method`` value the file carried, or ``None`` if it declared none."""

    def static_auth(self) -> BfabricAuth | None:
        """Credentials available without a network round trip."""
        return None

    def credential_provider(self, *, base_url: BaseUrl, env_name: str | None) -> OAuthCredentialProvider | None:
        """A token-refreshing provider, for methods that need one."""
        _ = base_url, env_name
        return None


class PasswordAuth(AuthMethodBase):
    kind: Literal["password"] = "password"
    login: str
    password: SecretStr

    owned_keys: ClassVar[frozenset[str]] = frozenset({"login", "password"})

    @override
    def static_auth(self) -> BfabricAuth:
        return BfabricAuth(login=self.login, password=self.password)


class PatAuth(AuthMethodBase):
    kind: Literal["pat"] = "pat"
    pat: SecretStr

    owned_keys: ClassVar[frozenset[str]] = frozenset({"pat"})

    @override
    def static_auth(self) -> BfabricAuth:
        return BfabricAuth(login=OAUTH_LOGIN, password=self.pat)


class InteractiveOAuthAuth(AuthMethodBase):
    kind: Literal["oauth"] = "oauth"
    client_id: str | None = None
    scope: str | None = None

    owned_keys: ClassVar[frozenset[str]] = frozenset({"client_id", "scope"})

    @override
    def credential_provider(self, *, base_url: BaseUrl, env_name: str | None) -> OAuthCredentialProvider:
        from bfabric.oauth._credential_provider import OAuthCredentialProvider
        from bfabric.oauth._token_cache import compute_token_cache_path

        if not self.client_id:
            raise ValueError(
                "OAuth config is missing 'client_id'. Set it in the config environment "
                "(e.g. re-run 'bfabric-cli auth login' or 'bfabric-cli auth device-code')."
            )
        if not env_name:
            raise ValueError(
                "OAuth config is missing 'env_name', so the token cache cannot be located. When "
                "configuring via BFABRICPY_CONFIG_OVERRIDE, include 'env_name' naming the "
                "environment whose cached token should be used."
            )
        return OAuthCredentialProvider.for_refresh(
            base_url=base_url,
            client_id=self.client_id,
            token_cache_path=compute_token_cache_path(base_url, self.client_id, env_name).expanduser(),
            require_cached_token=True,
        )


class ClientCredentialsAuth(AuthMethodBase):
    kind: Literal["client_credentials"] = "client_credentials"
    client_id: str | None = None
    client_secret: SecretStr | None = None
    scope: str | None = None

    owned_keys: ClassVar[frozenset[str]] = frozenset({"client_id", "client_secret", "scope"})

    @override
    def credential_provider(self, *, base_url: BaseUrl, env_name: str | None) -> OAuthCredentialProvider:
        from bfabric.oauth._credential_provider import OAuthCredentialProvider

        if not self.client_id:
            raise ValueError(
                "OAuth config is missing 'client_id'. Set it in the config environment "
                "(e.g. re-run 'bfabric-cli auth service-account')."
            )
        if self.client_secret is None:
            raise ValueError(
                "OAuth config is missing 'client_secret'. Set it in the config environment "
                "(e.g. re-run 'bfabric-cli auth service-account')."
            )
        return OAuthCredentialProvider.for_client_credentials(
            base_url=base_url,
            client_id=self.client_id,
            client_secret=self.client_secret.get_secret_value(),
            scope=self.scope or "",
        )


class NoAuth(AuthMethodBase):
    kind: Literal["none"] = "none"


class UnknownAuth(AuthMethodBase):
    """An ``auth_method`` this version does not know; usable for display, not for connecting."""

    kind: Literal["unknown"] = "unknown"
    unknown_name: str

    @override
    def credential_provider(self, *, base_url: BaseUrl, env_name: str | None) -> OAuthCredentialProvider:
        raise ValueError(
            f"Unknown auth_method {self.unknown_name!r} in the config environment. Upgrade bfabricPy "
            f"or set a supported auth_method."
        )


class ClientRegistration(BaseModel):
    """RFC 7592 credentials for editing this client's own registration."""

    registration_access_token: SecretStr
    registration_client_uri: str

    owned_keys: ClassVar[frozenset[str]] = frozenset({"registration_access_token", "registration_client_uri"})


AuthMethod = Annotated[
    PasswordAuth | PatAuth | InteractiveOAuthAuth | ClientCredentialsAuth | NoAuth | UnknownAuth,
    Field(discriminator="kind"),
]

AUTH_METHOD_CLASSES: tuple[type[AuthMethodBase], ...] = (
    PasswordAuth,
    PatAuth,
    InteractiveOAuthAuth,
    ClientCredentialsAuth,
    NoAuth,
    UnknownAuth,
)

_KNOWN_METHODS: frozenset[str] = frozenset(get_args(AuthMethodName))


def auth_owned_keys() -> frozenset[str]:
    """Every flat YAML key the auth layer owns."""
    keys = {"auth_method"} | set(ClientRegistration.owned_keys)
    for cls in AUTH_METHOD_CLASSES:
        keys |= cls.owned_keys
    return frozenset(keys)


def registration_from_flat(values: Mapping[str, object]) -> ClientRegistration | None:
    """Parse the registration credential pair; a half pair is tolerated as ``None``."""
    token = values.get("registration_access_token")
    uri = values.get("registration_client_uri")
    if token is None or uri is None:
        if token is not None or uri is not None:
            logger.warning("Ignoring incomplete registration credentials: both keys are required.")
        return None
    return ClientRegistration(registration_access_token=SecretStr(str(token)), registration_client_uri=str(uri))


def auth_method_from_flat(values: Mapping[str, object]) -> AuthMethodBase:
    """Parse a flat YAML environment into an auth method, tolerating incoherent stored state."""
    declared = values.get("auth_method")
    declared_name = str(declared) if declared is not None else None

    if declared_name is not None and declared_name not in _KNOWN_METHODS:
        return UnknownAuth(unknown_name=declared_name)

    if declared_name in (None, "password") and values.get("login") is not None:
        return PasswordAuth(
            declared_name="password" if declared_name == "password" else None,
            login=str(values["login"]),
            password=SecretStr(str(values.get("password", ""))),
        )

    if declared_name == "oauth":
        client_id = values.get("client_id")
        scope = values.get("scope")
        return InteractiveOAuthAuth(
            declared_name=declared_name,
            client_id=str(client_id) if client_id is not None else None,
            scope=str(scope) if scope is not None else None,
        )

    if declared_name == "client_credentials":
        client_id = values.get("client_id")
        secret = values.get("client_secret")
        scope = values.get("scope")
        return ClientCredentialsAuth(
            declared_name=declared_name,
            client_id=str(client_id) if client_id is not None else None,
            client_secret=SecretStr(str(secret)) if secret is not None else None,
            scope=str(scope) if scope is not None else None,
        )

    if values.get("pat"):
        return PatAuth(declared_name="pat" if declared_name == "pat" else None, pat=SecretStr(str(values["pat"])))

    if declared_name is None and (values.get("client_id") is not None or values.get("scope") is not None):
        client_id = values.get("client_id")
        scope = values.get("scope")
        return InteractiveOAuthAuth(
            client_id=str(client_id) if client_id is not None else None,
            scope=str(scope) if scope is not None else None,
        )

    if declared_name is not None:
        logger.warning(f"Environment declares auth_method {declared_name!r} but has no matching credentials.")
    return NoAuth()

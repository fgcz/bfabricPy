"""In-memory representation of how a config environment authenticates.

The on-disk YAML is flat (``auth_method`` plus sibling keys); :func:`auth_method_from_flat` is the
only place it is interpreted. Writing goes the other way round: the CLI hands
:func:`bfabric.config.config_writer.write_environment_to_config` the flat keys directly, so these
models are parse-only data and never serialise themselves back.

The variants carry no behaviour either: :func:`resolve_static_auth` and
:func:`resolve_credential_provider` turn a parsed method into credentials. They are kept apart
because static auth must be answerable from the environment alone, without a base URL, an
environment name or a look at the token cache.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, ClassVar, Literal, get_args

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
    """The ``auth_method`` the environment declared, ``None`` for a legacy or unsupported one."""


class PasswordAuth(AuthMethodBase):
    kind: Literal["password"] = "password"
    login: str
    password: SecretStr

    owned_keys: ClassVar[frozenset[str]] = frozenset({"login", "password"})


class PatAuth(AuthMethodBase):
    kind: Literal["pat"] = "pat"
    pat: SecretStr

    owned_keys: ClassVar[frozenset[str]] = frozenset({"pat"})


class InteractiveOAuthAuth(AuthMethodBase):
    kind: Literal["oauth"] = "oauth"
    client_id: str | None = None
    scope: str | None = None

    owned_keys: ClassVar[frozenset[str]] = frozenset({"client_id", "scope"})


class ClientCredentialsAuth(AuthMethodBase):
    kind: Literal["client_credentials"] = "client_credentials"
    client_id: str | None = None
    client_secret: SecretStr | None = None
    scope: str | None = None

    owned_keys: ClassVar[frozenset[str]] = frozenset({"client_id", "client_secret", "scope"})


class NoAuth(AuthMethodBase):
    kind: Literal["none"] = "none"


class UnknownAuth(AuthMethodBase):
    """An ``auth_method`` this version does not know; usable for display, not for connecting."""

    kind: Literal["unknown"] = "unknown"
    unknown_name: str


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


def _as_secret(value: object) -> SecretStr | None:
    """Wrap *value* as a secret, passing an existing :class:`SecretStr` through unmasked."""
    if value is None:
        return None
    return value if isinstance(value, SecretStr) else SecretStr(str(value))


def _as_str(value: object) -> str | None:
    return str(value) if value is not None else None


def _oauth_from_flat(values: Mapping[str, object], *, declared_name: AuthMethodName | None) -> InteractiveOAuthAuth:
    return InteractiveOAuthAuth(
        declared_name=declared_name,
        client_id=_as_str(values.get("client_id")),
        scope=_as_str(values.get("scope")),
    )


def registration_from_flat(values: Mapping[str, object]) -> ClientRegistration | None:
    """Parse the registration credential pair; a half pair is tolerated as ``None``."""
    token = values.get("registration_access_token")
    uri = values.get("registration_client_uri")
    if token is None or uri is None:
        if token is not None or uri is not None:
            logger.warning("Ignoring incomplete registration credentials: both keys are required.")
        return None
    secret = _as_secret(token)
    assert secret is not None  # noqa: S101 - `token is None` is excluded above
    return ClientRegistration(registration_access_token=secret, registration_client_uri=str(uri))


def auth_method_from_flat(values: Mapping[str, object]) -> AuthMethodBase:
    """Parse a flat YAML environment into an auth method, tolerating incoherent stored state."""
    raw_name = values.get("auth_method")
    declared = str(raw_name) if raw_name is not None else None

    if declared is not None and declared not in _KNOWN_METHODS:
        return UnknownAuth(unknown_name=declared)

    if declared in (None, "password") and values.get("login") is not None:
        return PasswordAuth(
            declared_name="password" if declared == "password" else None,
            login=str(values["login"]),
            password=_as_secret(values.get("password")) or SecretStr(""),
        )

    if declared == "oauth":
        return _oauth_from_flat(values, declared_name="oauth")

    if declared == "client_credentials":
        return ClientCredentialsAuth(
            declared_name="client_credentials",
            client_id=_as_str(values.get("client_id")),
            client_secret=_as_secret(values.get("client_secret")),
            scope=_as_str(values.get("scope")),
        )

    if values.get("pat"):
        return PatAuth(
            declared_name="pat" if declared == "pat" else None,
            pat=_as_secret(values["pat"]) or SecretStr(""),
        )

    if declared is None and (values.get("client_id") is not None or values.get("scope") is not None):
        return _oauth_from_flat(values, declared_name=None)

    if declared is not None:
        logger.warning(f"Environment declares auth_method {declared!r} but has no matching credentials.")
    return NoAuth()


def resolve_static_auth(method: AuthMethodBase) -> BfabricAuth | None:
    """The credentials *method* carries in the config file, without a network round trip."""
    match method:
        case PasswordAuth(login=login, password=password):
            return BfabricAuth(login=login, password=password)
        case PatAuth(pat=pat):
            return BfabricAuth(login=OAUTH_LOGIN, password=pat)
        case _:
            return None


def resolve_credential_provider(
    method: AuthMethodBase, *, base_url: BaseUrl, env_name: str | None
) -> OAuthCredentialProvider | None:
    """The token-refreshing provider *method* needs, or ``None`` if it authenticates statically.

    :raises ValueError: if *method* is unsupported, or is an OAuth method whose keys are incomplete.
    """
    match method:
        case InteractiveOAuthAuth():
            return _interactive_oauth_provider(method, base_url=base_url, env_name=env_name)
        case ClientCredentialsAuth():
            return _client_credentials_provider(method, base_url=base_url)
        case UnknownAuth(unknown_name=name):
            raise ValueError(
                f"Unknown auth_method {name!r} in the config environment. Upgrade bfabricPy "
                f"or set a supported auth_method."
            )
        case _:
            return None


def _interactive_oauth_provider(
    method: InteractiveOAuthAuth, *, base_url: BaseUrl, env_name: str | None
) -> OAuthCredentialProvider:
    from bfabric.oauth._credential_provider import OAuthCredentialProvider
    from bfabric.oauth._token_cache import compute_token_cache_path

    if not method.client_id:
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
        client_id=method.client_id,
        token_cache_path=compute_token_cache_path(base_url, method.client_id, env_name).expanduser(),
        require_cached_token=True,
    )


def _client_credentials_provider(method: ClientCredentialsAuth, *, base_url: BaseUrl) -> OAuthCredentialProvider:
    from bfabric.oauth._credential_provider import OAuthCredentialProvider

    if not method.client_id:
        raise ValueError(
            "OAuth config is missing 'client_id'. Set it in the config environment "
            "(e.g. re-run 'bfabric-cli auth service-account')."
        )
    if method.client_secret is None:
        raise ValueError(
            "OAuth config is missing 'client_secret'. Set it in the config environment "
            "(e.g. re-run 'bfabric-cli auth service-account')."
        )
    return OAuthCredentialProvider.for_client_credentials(
        base_url=base_url,
        client_id=method.client_id,
        client_secret=method.client_secret.get_secret_value(),
        scope=method.scope or "",
    )

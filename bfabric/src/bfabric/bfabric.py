"""B-Fabric Application Interface using WSDL

Copyright (C) 2014 - 2024 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Licensed under GPL version 3

Authors:
  Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
  Christian Panse <cp@fgcz.ethz.ch>
  Leonardo Schwarz
  Aleksejs Fomins
"""

from __future__ import annotations

import asyncio
import base64
import importlib.metadata
import sys
import warnings
from contextlib import contextmanager
from datetime import datetime
from functools import cached_property
from pathlib import Path
from pprint import pprint
from typing import TYPE_CHECKING, Any, Literal

from loguru import logger
from rich.console import Console

from bfabric._oauth._constants import DEFAULT_CLIENT_ID, DEFAULT_OAUTH_SCOPE

from bfabric.config import BfabricAuth, BfabricClientConfig, DEFAULT_CONFIG_FILE
from bfabric.config.bfabric_client_config import BfabricAPIEngineType
from bfabric.config.config_data import ConfigData, load_config_data
from bfabric.config.config_file import read_config_file
from bfabric.engine.engine_suds import EngineSUDS
from bfabric.engine.engine_zeep import EngineZeep
from bfabric.rest.token_data import TokenData, get_token_data, validate_token
from bfabric.results.result_container import ResultContainer
from bfabric.utils.cli_integration import DEFAULT_THEME, HostnameHighlighter
from bfabric.utils.paginator import BFABRIC_QUERY_LIMIT, compute_requested_pages

if TYPE_CHECKING:
    from collections.abc import Generator

    from pydantic import SecretStr

    from bfabric.entities.core.entity_reader import EntityReader
    from bfabric.experimental.webapp_integration_settings import TokenValidationSettingsProtocol
    from bfabric._oauth.credential_provider import OAuthCredentialProvider
    from bfabric._oauth.url_token import UrlTokenContext
    from bfabric.typing import ApiRequestObjectType, ApiResponseObjectType


class Bfabric:
    """Bfabric client class, providing general functionality for interaction with the B-Fabric API.

    Use `Bfabric.connect()` or `Bfabric.connect_webapp` to create a new instance, and check out their docstrings for
    more details on how to use.
    """

    _credential_provider: OAuthCredentialProvider | None

    def __init__(
        self,
        config_data: ConfigData,
        *,
        _credential_provider: OAuthCredentialProvider | None = None,
    ) -> None:
        self.query_counter = 0
        self._config = config_data.client
        self._auth = config_data.auth
        self._credential_provider = _credential_provider
        self._log_version_message()

    @cached_property
    def _engine(self) -> EngineSUDS | EngineZeep:
        if self.config.engine == BfabricAPIEngineType.SUDS:
            return EngineSUDS(base_url=self._config.base_url)
        elif self.config.engine == BfabricAPIEngineType.ZEEP:
            return EngineZeep(base_url=self._config.base_url)
        else:
            raise ValueError(f"Unexpected engine type: {self.config.engine}")

    @classmethod
    def connect(
        cls,
        *,
        config_file_path: Path | str = DEFAULT_CONFIG_FILE,
        config_file_env: str | Literal["default"] | None = "default",
        include_auth: bool = True,
    ) -> Bfabric:
        """Returns a new Bfabric instance.

        If a `BFABRICPY_CONFIG_OVERRIDE` environment variable is set, all configuration will originate from it.

        If it's not present, and `config_file_env` is not `None`, your config file (`~/.bfabricpy.yml` by default) will
        be used instead.
        If `config_file_env` is `"default"`, then if available the environment according to env variable
        `BFABRICPY_CONFIG_ENV` will be used, otherwise the default environment in the config file will be used.
        Otherwise, `config_file_env` specifies the name of the environment.

        :param config_file_path: a non-standard configuration file to use, if config file is selected as a config source
        :param config_file_env: name of environment to use, if config file is selected as a config source.
            if `"default"` is specified, the default environment will be used.
            if `None` is specified, the file will not be used as a config source.
        :param include_auth: whether auth information should be included (for servers, setting this to False is useful)
        """
        config_data = load_config_data(
            config_file_path=config_file_path, include_auth=include_auth, config_file_env=config_file_env
        )
        if config_data.auth_method == "oauth":
            return cls._connect_oauth_from_config(config_data)
        return cls(config_data=config_data)

    @classmethod
    def _connect_oauth_from_config(cls, config_data: ConfigData) -> Bfabric:
        """Create a Bfabric instance from a config with ``auth_method: oauth``.

        Loads tokens from the disk cache keyed on ``base_url`` + ``client_id``.
        """
        from bfabric._oauth.credential_provider import OAuthCredentialProvider
        from bfabric._oauth.token_cache import TokenCache, compute_token_cache_path

        base_url = config_data.client.base_url.rstrip("/")
        client_id = config_data.client_id or DEFAULT_CLIENT_ID
        env_name = config_data.env_name or "default"
        cache_path = compute_token_cache_path(base_url, client_id, env_name).expanduser()
        if not TokenCache(cache_path).load():
            raise ValueError("No OAuth tokens found. Run 'bfabric-cli auth pkce' or 'bfabric-cli auth device-code'.")
        provider = OAuthCredentialProvider(
            client_id=client_id,
            client_secret="",
            token_url=f"{base_url}/rest/oauth/token",
            grant_type="refresh_token",
            token_cache_path=cache_path,
        )
        return cls(config_data=config_data, _credential_provider=provider)

    @classmethod
    def from_config(
        cls,
        config_env: str | None = None,
        config_path: str | None = None,
        auth: BfabricAuth | Literal["config"] | None = "config",
        engine: BfabricAPIEngineType | None = None,
    ) -> Bfabric:
        """Returns a new Bfabric instance, configured with the user configuration file.
        If the `config_env` is specified then it will be used, if it is not specified the default environment will be
        determined by checking the following in order (picking the first one that is found):
        - The `BFABRICPY_CONFIG_ENV` environment variable
        - The `default_config` field in the config file "GENERAL" section

        :param config_env: Configuration environment to use. If not given, it is deduced as described above.
        :param config_path: Path to the config file, in case it is different from default
        :param auth: Authentication to use. If "config" is given, the authentication will be read from the config file.
             If it is set to None, no authentication will be used.
        :param engine: Engine to use for the API.
        """
        warnings.warn(
            "Bfabric.from_config() is deprecated and will be removed in a future release. "
            "Use Bfabric.connect() instead."
        )
        config, auth_config = get_system_auth(config_env=config_env, config_path=config_path)
        auth_used: BfabricAuth | None = auth_config if auth == "config" else auth
        # TODO https://github.com/fgcz/bfabricPy/issues/164
        # if engine is not None:
        #    config = config.copy_with(engine=engine)
        return cls(ConfigData(client=config, auth=auth_used))

    @classmethod
    def from_token_data(cls, token_data: TokenData) -> Bfabric:
        """Creates a new Bfabric instance from token data."""
        config_data_client = BfabricClientConfig.model_validate(dict(base_url=token_data.caller))
        config_data_auth = BfabricAuth(login=token_data.user, password=token_data.user_ws_password)
        config_data = ConfigData(client=config_data_client, auth=config_data_auth)
        return cls(config_data=config_data)

    @classmethod
    def connect_webapp(
        cls,
        token: str,
        *,
        validation_instance_url: str = "https://fgcz-bfabric.uzh.ch/bfabric/",
        config_file_path: None = None,
        config_file_env: None = None,
    ) -> tuple[Bfabric, TokenData]:
        """Returns a new Bfabric instance, configured with the user configuration file and the provided token.

        :param token: the token to use for authentication
        :param validation_instance_url: the URL of the B-Fabric instance to use for token validation, in principle
            validation can be performed on any B-Fabric instance as the token describes the caller too
        :return: a tuple of the Bfabric instance and the token data
        """
        _ = config_file_path, config_file_env
        warnings.warn(
            "use Bfabric.connect_token which allows for a more secure set up",
            DeprecationWarning,
        )
        token_data = get_token_data(base_url=validation_instance_url, token=token)
        return cls.from_token_data(token_data), token_data

    @classmethod
    def connect_token(
        cls, token: str | SecretStr, settings: TokenValidationSettingsProtocol
    ) -> tuple[Bfabric, TokenData]:
        """Returns a new Bfabric instance configured with the provided token.

        Calls connect_token_async, if you are in a coroutine then you have to call connect_token_async instead.
        """
        return asyncio.run(cls.connect_token_async(token=token, settings=settings))

    @classmethod
    async def connect_token_async(
        cls, token: str | SecretStr, settings: TokenValidationSettingsProtocol
    ) -> tuple[Bfabric, TokenData]:
        """Returns a new Bfabric instance configured with the provided token.

        Settings needs to be configured to allow the desired B-Fabric instances.
        """
        token_data = await validate_token(token=token, settings=settings)
        return cls.from_token_data(token_data), token_data

    @classmethod
    def connect_oauth(
        cls,
        client_id: str,
        client_secret: str,
        base_url: str,
        *,
        scope: str = DEFAULT_OAUTH_SCOPE,
        token_cache_path: Path | None = None,
    ) -> Bfabric:
        """Returns a new Bfabric instance that authenticates via OAuth 2.0 client credentials.

        Tokens are fetched and refreshed automatically. Every SOAP call gets a
        fresh ``BfabricAuth(login="__oauth__", password=<jwt>)`` via the
        credential provider.

        :param client_id: OAuth client ID (from ``register_client`` or admin setup)
        :param client_secret: OAuth client secret
        :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
        :param scope: OAuth scope (default ``"api:read api:write"``)
        :param token_cache_path: Optional path to cache tokens on disk (survives restarts)
        """
        from bfabric._oauth.credential_provider import OAuthCredentialProvider

        base_url = base_url.rstrip("/")
        token_url = f"{base_url}/rest/oauth/token"
        provider = OAuthCredentialProvider(
            client_id=client_id,
            client_secret=client_secret,
            token_url=token_url,
            scope=scope,
            grant_type="client_credentials",
            token_cache_path=token_cache_path,
        )
        config = BfabricClientConfig(base_url=base_url)  # pyright: ignore[reportCallIssue]
        config_data = ConfigData(client=config, auth=None)
        return cls(config_data=config_data, _credential_provider=provider)

    @classmethod
    def from_url_token(
        cls,
        base_url: str,
        jwt: str,
        refresh_token: str | None = None,
        *,
        token_cache_path: Path | None = None,
    ) -> tuple[Bfabric, UrlTokenContext]:
        """Creates a new Bfabric instance from a B-Fabric URL token JWT.

        Verifies the JWT signature via JWKS and extracts entity context
        (entity_id, application_id, etc.) from the token claims.

        If *refresh_token* is provided, the access token is automatically
        refreshed when it expires. Without a refresh token, the JWT is used
        as-is and the caller must handle expiry.

        :param base_url: B-Fabric instance URL
        :param jwt: The raw JWT string from the URL ``jwt`` parameter
        :param refresh_token: Optional refresh token for automatic renewal
        :param token_cache_path: Optional path to cache tokens on disk
        :returns: Tuple of ``(Bfabric, UrlTokenContext)``
        """
        from bfabric.config.bfabric_auth import OAUTH_LOGIN
        from bfabric._oauth.url_token import parse_url_token

        base_url = base_url.rstrip("/")
        context = parse_url_token(base_url, jwt)

        provider: OAuthCredentialProvider | None = None
        if refresh_token is not None:
            from bfabric._oauth.credential_provider import OAuthCredentialProvider

            token_url = f"{base_url}/rest/oauth/token"
            # client_id is embedded in the JWT by B-Fabric; public client (no secret)
            client_id = context.client_id or ""
            token_dict: dict[str, object] = {
                "access_token": jwt,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
            }
            if context.expires_at is not None:
                token_dict["expires_at"] = context.expires_at.timestamp()
            provider = OAuthCredentialProvider(
                client_id=client_id,
                client_secret="",
                token_url=token_url,
                token=token_dict,
                grant_type="refresh_token",
                token_cache_path=token_cache_path,
            )

        config = BfabricClientConfig(base_url=base_url)  # pyright: ignore[reportCallIssue]
        if provider is not None:
            config_data = ConfigData(client=config, auth=None)
            return cls(config_data=config_data, _credential_provider=provider), context
        else:
            if context.expires_at is not None and context.expires_at <= datetime.now(tz=context.expires_at.tzinfo):
                from bfabric.errors import BfabricTokenExpiredError

                raise BfabricTokenExpiredError()
            auth = BfabricAuth(login=OAUTH_LOGIN, password=jwt)  # pyright: ignore[reportArgumentType]
            config_data = ConfigData(client=config, auth=auth)
            return cls(config_data=config_data), context

    @classmethod
    def connect_pkce(
        cls,
        base_url: str,
        *,
        client_id: str = DEFAULT_CLIENT_ID,
        scope: str = DEFAULT_OAUTH_SCOPE,
        port: int = 0,
        open_browser: bool = True,
        timeout: float = 120.0,
        token_cache_path: Path | None = None,
    ) -> Bfabric:
        """Returns a new Bfabric instance after interactive browser-based PKCE login.

        Opens the user's browser to the B-Fabric authorization page.  After
        the user logs in, tokens are exchanged automatically and the returned
        client uses :class:`OAuthCredentialProvider` for transparent refresh.

        :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
        :param client_id: OAuth client ID (default ``"bfabric-cli"``)
        :param scope: OAuth scope (default ``"api:read api:write"``)
        :param port: Local port for the callback server (``0`` = auto-assign)
        :param open_browser: Whether to open the authorization URL in the browser
        :param timeout: Seconds to wait for the user to complete login
        :param token_cache_path: Optional path to cache tokens on disk (survives restarts)
        """
        from bfabric._oauth.credential_provider import OAuthCredentialProvider
        from bfabric._oauth.pkce import pkce_login

        base_url = base_url.rstrip("/")
        token = pkce_login(
            base_url,
            client_id=client_id,
            scope=scope,
            port=port,
            open_browser=open_browser,
            timeout=timeout,
        )
        token_url = f"{base_url}/rest/oauth/token"
        provider = OAuthCredentialProvider(
            client_id=client_id,
            client_secret="",
            token_url=token_url,
            token=token,
            grant_type="refresh_token",
            scope=scope,
            token_cache_path=token_cache_path,
        )
        config = BfabricClientConfig(base_url=base_url)  # pyright: ignore[reportCallIssue]
        config_data = ConfigData(client=config, auth=None)
        return cls(config_data=config_data, _credential_provider=provider)

    @classmethod
    def connect_device_code(
        cls,
        base_url: str,
        *,
        client_id: str = DEFAULT_CLIENT_ID,
        scope: str = DEFAULT_OAUTH_SCOPE,
        timeout: float = 600.0,
        token_cache_path: Path | None = None,
    ) -> Bfabric:
        """Returns a new Bfabric instance after device code authorization (RFC 8628).

        Displays a user code and verification URI on stderr.  The user
        visits the URI, enters the code, and authorizes the device.  The
        returned client uses :class:`OAuthCredentialProvider` for transparent
        token refresh.

        This flow is suitable for headless environments (SSH, containers)
        where a localhost redirect is not feasible.

        :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
        :param client_id: OAuth client ID (default ``"bfabric-cli"``)
        :param scope: OAuth scope (default ``"api:read api:write"``)
        :param timeout: Seconds to wait for the user to authorize (default 600)
        :param token_cache_path: Optional path to cache tokens on disk (survives restarts)
        """
        from bfabric._oauth.credential_provider import OAuthCredentialProvider
        from bfabric._oauth.device_code import device_code_login

        base_url = base_url.rstrip("/")
        token = device_code_login(
            base_url,
            client_id=client_id,
            scope=scope,
            timeout=timeout,
        )
        token_url = f"{base_url}/rest/oauth/token"
        provider = OAuthCredentialProvider(
            client_id=client_id,
            client_secret="",
            token_url=token_url,
            token=token,
            grant_type="refresh_token",
            scope=scope,
            token_cache_path=token_cache_path,
        )
        config = BfabricClientConfig(base_url=base_url)  # pyright: ignore[reportCallIssue]
        config_data = ConfigData(client=config, auth=None)
        return cls(config_data=config_data, _credential_provider=provider)

    @classmethod
    def connect_pat(
        cls,
        base_url: str,
        pat: str | SecretStr,
    ) -> Bfabric:
        """Returns a new Bfabric instance that authenticates via a Personal Access Token.

        PATs are opaque bearer tokens issued by B-Fabric. Unlike JWTs they
        cannot be verified locally, but they also don't need to be — the SOAP
        API accepts them directly. There is no automatic refresh; if the token
        expires a new one must be obtained.

        :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
        :param pat: Personal Access Token (string or ``SecretStr``)
        """
        from pydantic import SecretStr as _SecretStr

        from bfabric.config.bfabric_auth import OAUTH_LOGIN

        base_url = base_url.rstrip("/")
        pat_value = pat.get_secret_value() if isinstance(pat, _SecretStr) else pat
        auth = BfabricAuth(login=OAUTH_LOGIN, password=pat_value)  # pyright: ignore[reportArgumentType]
        config = BfabricClientConfig(base_url=base_url)  # pyright: ignore[reportCallIssue]
        config_data = ConfigData(client=config, auth=auth)
        return cls(config_data=config_data)

    @staticmethod
    def parse_url_token(base_url: str, jwt: str) -> UrlTokenContext:
        """Verify and parse a B-Fabric URL token without creating a Bfabric instance.

        Useful when a webapp needs to read context from the URL token
        (entity_id, user, application_id) but uses its own client credentials
        (via :meth:`connect_oauth`) for API calls.

        :param base_url: B-Fabric instance URL
        :param jwt: The raw JWT string from the URL ``jwt`` parameter
        :returns: :class:`UrlTokenContext` with the extracted claims
        """
        from bfabric._oauth.url_token import parse_url_token

        return parse_url_token(base_url.rstrip("/"), jwt)

    @property
    def config(self) -> BfabricClientConfig:
        """Returns the config object."""
        return self._config

    @property
    def auth(self) -> BfabricAuth:
        """Returns the auth object.

        When a credential provider is present (OAuth), it returns a fresh
        :class:`BfabricAuth` with the current access token.

        :raises ValueError: If authentication is not available
        """
        if self._credential_provider is not None:
            return self._credential_provider.get_auth()
        if self._auth is None:
            raise ValueError("Authentication not available")
        return self._auth

    @property
    def config_data(self) -> ConfigData:
        """Returns the config data object."""
        return ConfigData(client=self._config, auth=self._auth)

    @contextmanager
    def with_auth(self, auth: BfabricAuth) -> Generator[None, None, None]:
        """Context manager that temporarily (within the scope of the context) sets the authentication for
        the Bfabric object to the provided value. This is useful when authenticating multiple users, to avoid accidental
        use of the wrong credentials.

        When a credential provider is active, it is temporarily disabled so the
        explicit *auth* takes priority.
        """
        old_auth = self._auth
        old_provider = self._credential_provider
        self._auth = auth
        self._credential_provider = None
        try:
            yield
        finally:
            self._auth = old_auth
            self._credential_provider = old_provider

    @cached_property
    def reader(self) -> EntityReader:
        """Returns an EntityReader for this client."""
        from bfabric.entities.core.entity_reader import EntityReader

        return EntityReader.for_client(client=self)

    def read(
        self,
        endpoint: str,
        obj: ApiRequestObjectType,
        max_results: int | None = 100,
        offset: int = 0,
        check: bool = True,
        return_id_only: bool = False,
    ) -> ResultContainer:
        """Reads from the specified endpoint matching all specified attributes in `obj`.

        By setting `max_results` it is possible to change the number of results that are returned.

        :param endpoint: The B-Fabric endpoint to query (e.g., "sample", "project", "workunit").
        :param obj: A dictionary containing the query criteria. For every field, multiple possible values
            can be provided as a list (treated as OR). Multiple fields are treated as AND.
        :param max_results: Maximum number of results to return. The client will automatically handle
            pagination to reach this limit. Set to ``None`` to retrieve all available results.
            Note: results are fetched in blocks of 100.
        :param offset: Number of results to skip before starting to return results.
        :param check: If ``True`` (default), raises a ``RuntimeError`` if the query fails.
        :param return_id_only: If ``True``, only returns entity IDs instead of full data (faster).
        :return: A :class:`ResultContainer` containing the query results.
        """
        # Get the first page.
        logger.debug(f"Reading from endpoint {repr(endpoint)} with query {repr(obj)}")
        results = self._engine.read(
            endpoint=endpoint,
            obj=obj,
            auth=self.auth,
            page=1,
            return_id_only=return_id_only,
        )
        n_available_pages = results.total_pages_api
        if not n_available_pages:
            if check:
                results.assert_success()
            return results.get_first_n_results(max_results)

        # Get results from other pages as well, if need be
        requested_pages, initial_offset = compute_requested_pages(
            n_page_total=n_available_pages,
            n_item_per_page=BFABRIC_QUERY_LIMIT,
            n_item_offset=offset,
            n_item_return_max=max_results,
        )
        logger.debug(f"Requested pages: {requested_pages}")

        # NOTE: Page numbering starts at 1
        response_items: list[ApiResponseObjectType] = []
        errors = results.errors
        page_offset = initial_offset
        for i_iter, i_page in enumerate(requested_pages):
            if not (i_iter == 0 and i_page == 1):
                logger.debug(f"Reading page {i_page} of {n_available_pages}")
                results = self._engine.read(
                    endpoint=endpoint,
                    obj=obj,
                    auth=self.auth,
                    page=i_page,
                    return_id_only=return_id_only,
                )
                errors += results.errors

            response_items += results[page_offset:]
            page_offset = 0

        result = ResultContainer(response_items, total_pages_api=n_available_pages, errors=errors)
        if check:
            result.assert_success()
        return result.get_first_n_results(max_results)

    def save(
        self,
        endpoint: str,
        obj: ApiRequestObjectType | list[ApiRequestObjectType],
        check: bool = True,
        method: str = "save",
    ) -> ResultContainer:
        """Saves the provided object to the specified endpoint.
        :param endpoint: the endpoint to save to, e.g. "sample"
        :param obj: the object(s) to save
        :param check: whether to raise an error if the response is not successful
        :param method: the method to use for saving, generally "save", but in some cases e.g. "update" is more
        appropriate to be used instead.

        :return a ResultContainer describing the saved object if successful
        """
        results = self._engine.save(endpoint=endpoint, obj=obj, auth=self.auth, method=method)
        if check:
            results.assert_success()
        return results

    def delete(self, endpoint: str, id: int | list[int], check: bool = True) -> ResultContainer:
        """Deletes the object with the specified ID from the specified endpoint.
        :param endpoint: the endpoint to delete from, e.g. "sample"
        :param id: the ID of the object to delete
        :param check: whether to raise an error if the response is not successful
        :return a ResultContainer describing the deleted object if successful
        """
        results = self._engine.delete(endpoint=endpoint, id=id, auth=self.auth)
        if check:
            results.assert_success()
        return results

    def exists(
        self,
        endpoint: str,
        key: str,
        value: int | str,
        query: ApiRequestObjectType | None = None,
        check: bool = True,
    ) -> bool:
        """Returns whether an object with the specified key-value pair exists in the specified endpoint.
        Further conditions can be specified in the query.
        :param endpoint: the endpoint to check, e.g. "sample"
        :param key: the key to check, e.g. "id"
        :param value: the value to check, e.g. 123
        :param query: additional query conditions (optional)
        :param check: whether to raise an error if the response is not successful
        """
        query = query or {}
        results = self.read(
            endpoint=endpoint,
            obj={**query, key: value},
            max_results=1,
            check=check,
            return_id_only=True,
        )
        return len(results) > 0

    def upload_resource(
        self, resource_name: str, content: bytes, workunit_id: int, check: bool = True
    ) -> ResultContainer:
        """Uploads a resource to B-Fabric, only intended for relatively small files that will be tracked by B-Fabric
        and not one of the dedicated experimental data stores.
        :param resource_name: the name of the resource to create (the same name can only exist once per workunit)
        :param content: the content of the resource as bytes
        :param workunit_id: the workunit ID to which the resource belongs
        :param check: whether to check for errors in the response
        """
        content_encoded = base64.b64encode(content).decode()
        return self.save(
            endpoint="resource",
            obj={
                "base64": content_encoded,
                "name": resource_name,
                "description": "base64 encoded file",
                "workunitid": workunit_id,
            },
            check=check,
        )

    def _get_version_message(self) -> tuple[str, str]:
        """Returns the version message as a string."""
        package_version = importlib.metadata.version("bfabric")
        year = datetime.now().year
        engine_name = self._engine.__class__.__name__
        base_url = self.config.base_url
        user_name = f"U={self._auth.login if self._auth else None}"
        python_version = f"PY={sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        return (
            f"bfabricPy v{package_version} ({engine_name}, {base_url}, {user_name}, {python_version})",
            f"Copyright (C) 2014-{year} Functional Genomics Center Zurich",
        )

    def _log_version_message(self) -> None:
        """Logs the version message describing bfabricpy version, engine and base url."""
        console = Console(highlighter=HostnameHighlighter(), theme=DEFAULT_THEME)
        for line in self._get_version_message():
            with console.capture() as capture:
                console.print(line, style="bright_yellow", end="")
            logger.info(capture.get())

    def __repr__(self) -> str:
        config_data = ConfigData(client=self._config, auth=self._auth)
        return f"Bfabric({config_data=})"

    __str__ = __repr__

    def __getstate__(self) -> dict[str, Any]:
        return {
            "config": self._config,
            "auth": self._auth,
            "query_counter": self.query_counter,
            "credential_provider": self._credential_provider,
        }

    def __setstate__(self, state: dict[str, Any]) -> None:
        self._config = state["config"]
        self._auth = state["auth"]
        self.query_counter = state["query_counter"]
        # .get for backward compatibility with pickles created before the provider was retained.
        self._credential_provider = state.get("credential_provider")


def get_system_auth(
    login: str | None = None,
    password: str | None = None,
    base_url: str | None = None,
    config_path: str | None = None,
    config_env: str | None = None,
    optional_auth: bool = True,
    verbose: bool = False,
) -> tuple[BfabricClientConfig, BfabricAuth | None]:
    """
    :param login:           Login string for overriding config file
    :param password:        Password for overriding config file
    :param base_url:        Base server url for overriding config file
    :param config_path:     Path to the config file, in case it is different from default
    :param config_env:      Which config environment to use. Can also specify via environment variable or use
       default in the config file (at your own risk)
    :param optional_auth:   Whether authentication is optional. If yes, missing authentication will be ignored,
       otherwise an exception will be raised
    :param verbose:         Verbosity (TODO: resolve potential redundancy with logger)
    """
    warnings.warn(
        "get_system_auth is deprecated, use Bfabric.connect or Bfabric.from_token instead", DeprecationWarning
    )

    resolved_path = Path(config_path or "~/.bfabricpy.yml").expanduser()

    # Use the provided config data from arguments instead of the file
    if not resolved_path.is_file():
        if config_path:
            # NOTE: If user explicitly specifies a path to a wrong config file, this has to be an exception
            raise OSError(f"Explicitly specified config file does not exist: {resolved_path}")
        # TODO: Convert to log
        print(f"Warning: could not find the config file in the default location: {resolved_path}")
        config = BfabricClientConfig(base_url=base_url)
        auth = None if login is None or password is None else BfabricAuth(login=login, password=password)

    # Load config from file, override some of the fields with the provided ones
    else:
        config, auth = read_config_file(resolved_path, config_env=config_env)
        config = config.copy_with(base_url=base_url)
        if (login is not None) and (password is not None):
            auth = BfabricAuth(login=login, password=password)
        elif (login is None) and (password is None):
            pass
        else:
            raise OSError("Must provide both username and password, or neither.")

    if not config.base_url:
        raise ValueError("base_url missing")
    if not optional_auth and (not auth or not auth.login or not auth.password):
        raise ValueError("Authentication not initialized but required")

    if verbose:
        pprint(config)

    return config, auth

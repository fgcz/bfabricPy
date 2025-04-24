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

import base64
import importlib.metadata
import sys
import warnings
from contextlib import contextmanager
from datetime import datetime
from functools import cached_property
from pathlib import Path
from pprint import pprint
from typing import Literal, Any, TYPE_CHECKING

from loguru import logger
from rich.console import Console

from bfabric.config import BfabricAuth
from bfabric.config import BfabricClientConfig
from bfabric.config.bfabric_client_config import BfabricAPIEngineType
from bfabric.config.config_data import ConfigData, load_config_data
from bfabric.config.config_file import read_config_file
from bfabric.engine.engine_suds import EngineSUDS
from bfabric.engine.engine_zeep import EngineZeep
from bfabric.rest.token_data import get_token_data, TokenData
from bfabric.results.result_container import ResultContainer
from bfabric.utils.cli_integration import DEFAULT_THEME, HostnameHighlighter
from bfabric.utils.paginator import compute_requested_pages, BFABRIC_QUERY_LIMIT

if TYPE_CHECKING:
    from collections.abc import Generator


class Bfabric:
    """Bfabric client class, providing general functionality for interaction with the B-Fabric API.

    Use `Bfabric.connect()` or `Bfabric.connect_webapp` to create a new instance, and check out their docstrings for
    more details on how to use.
    """

    def __init__(self, config_data: ConfigData) -> None:
        self.query_counter = 0
        self._config = config_data.client
        self._auth = config_data.auth
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
        config_file_path: Path | str = Path("~/.bfabricpy.yml"),
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
        return cls(config_data=config_data)

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
        config, auth_config = get_system_auth(config_env=config_env, config_path=config_path)
        auth_used: BfabricAuth | None = auth_config if auth == "config" else auth
        # TODO https://github.com/fgcz/bfabricPy/issues/164
        # if engine is not None:
        #    config = config.copy_with(engine=engine)
        return cls(ConfigData(client=config, auth=auth_used))

    @classmethod
    def connect_webapp(
        cls,
        token: str,
        *,
        config_file_path: Path | str = Path("~/.bfabricpy.yml"),
        config_file_env: str | Literal["default"] | None = "default",
    ) -> tuple[Bfabric, TokenData]:
        """Returns a new Bfabric instance, configured with the user configuration file and the provided token.

        Any authentication in the configuration file will be ignored, but it will be used to determine the correct
        B-Fabric instance.
        :param token: the token to use for authentication
        :param config_file_path: a non-standard configuration file to use, if config file is selected as a config source
        :param config_file_env: name of environment to use, if config file is selected as a config source.
            if `"default"` is specified, the default environment will be used.
            if `None` is specified, the file will not be used as a config source.
        :return: a tuple of the Bfabric instance and the token data
        """
        config_data = load_config_data(
            config_file_path=config_file_path, include_auth=False, config_file_env=config_file_env
        )
        client_config = config_data.client
        token_data = get_token_data(client_config=client_config, token=token)
        auth = BfabricAuth(login=token_data.user, password=token_data.user_ws_password)
        return cls(config_data.with_auth(auth)), token_data

    @property
    def config(self) -> BfabricClientConfig:
        """Returns the config object."""
        return self._config

    @property
    def auth(self) -> BfabricAuth:
        """Returns the auth object.
        :raises ValueError: If authentication is not available
        """
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
        """
        old_auth = self._auth
        self._auth = auth
        try:
            yield
        finally:
            self._auth = old_auth

    def read(
        self,
        endpoint: str,
        obj: dict[str, Any],
        max_results: int | None = 100,
        offset: int = 0,
        check: bool = True,
        return_id_only: bool = False,
    ) -> ResultContainer:
        """Reads from the specified endpoint matching all specified attributes in `obj`.
        By setting `max_results` it is possible to change the number of results that are returned.
        :param endpoint: the endpoint to read from, e.g. "sample"
        :param obj: a dictionary containing the query, for every field multiple possible values can be provided, the
            final query requires the condition for each field to be met
        :param max_results: cap on the number of results to query. The code will keep reading pages until all pages
           are read or expected number of results has been reached. If None, load all available pages.
           NOTE: max_results will be rounded upwards to the nearest multiple of BFABRIC_QUERY_LIMIT, because results
           come in blocks, and there is little overhead to providing results over integer number of pages.
        :param offset: the number of elements to skip before starting to return results (useful for pagination, default
              is 0 which means no skipping)
        :param check: whether to raise an error if the response is not successful
        :param return_id_only: whether to return only the ids of the found objects
        :return: List of responses, packaged in the results container
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
        response_items: list[dict[str, Any]] = []
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
        obj: dict[str, Any],
        check: bool = True,
        method: str = "save",
    ) -> ResultContainer:
        """Saves the provided object to the specified endpoint.
        :param endpoint: the endpoint to save to, e.g. "sample"
        :param obj: the object to save
        :param check: whether to raise an error if the response is not successful
        :param method: the method to use for saving, generally "save", but in some cases e.g. "checkandinsert" is more
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
        query: dict[str, Any] | None = None,
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
        }

    def __setstate__(self, state: dict[str, Any]) -> None:
        self._config = state["config"]
        self._auth = state["auth"]
        self.query_counter = state["query_counter"]


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

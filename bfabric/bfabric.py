#!/usr/bin/env python3
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
import logging
import sys
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from pprint import pprint
from typing import Literal, ContextManager, Any

from rich.console import Console

from bfabric.bfabric_config import BfabricAuth, read_config
from bfabric.bfabric_config import BfabricConfig
from bfabric.cli_formatting import HostnameHighlighter, DEFAULT_THEME
from bfabric.engine.engine_suds import EngineSUDS
from bfabric.engine.engine_zeep import EngineZeep
from bfabric.results.result_container import ResultContainer
from bfabric.utils.paginator import compute_requested_pages, BFABRIC_QUERY_LIMIT


class BfabricAPIEngineType(Enum):
    """Choice of engine to use."""

    SUDS = 1
    ZEEP = 2


# TODO: How to deal with save-skip fields in Zeep? Does it happen in SUDS?
class Bfabric:
    """Bfabric client class, providing general functionality for interaction with the B-Fabric API.
    Use `Bfabric.from_config` to create a new instance.
    :param config: Configuration object
    :param auth: Authentication object (if `None`, it has to be provided using the `with_auth` context manager)
    :param engine: Engine to use for the API. Default is SUDS.
    :param verbose: Print a system info message to standard error console
    """

    def __init__(
        self,
        config: BfabricConfig,
        auth: BfabricAuth | None,
        engine: BfabricAPIEngineType = BfabricAPIEngineType.SUDS,
        verbose: bool = False,
    ) -> None:
        self.query_counter = 0
        self._config = config
        self._auth = auth

        if engine == BfabricAPIEngineType.SUDS:
            self.engine = EngineSUDS(base_url=config.base_url)
        elif engine == BfabricAPIEngineType.ZEEP:
            self.engine = EngineZeep(base_url=config.base_url)
        else:
            raise ValueError(f"Unexpected engine: {engine}")

        if verbose:
            self.print_version_message()

    @classmethod
    def from_config(
        cls,
        config_env: str | None = None,
        config_path: str | None = None,
        auth: BfabricAuth | Literal["config"] | None = "config",
        engine: BfabricAPIEngineType = BfabricAPIEngineType.SUDS,
        verbose: bool = False,
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
        :param engine: Engine to use for the API. Default is SUDS.
        :param verbose: Print a system info message to standard error console
        """
        config, auth_config = get_system_auth(config_env=config_env, config_path=config_path)
        auth_used: BfabricAuth | None = auth_config if auth == "config" else auth
        return cls(config, auth_used, engine=engine, verbose=verbose)

    @property
    def config(self) -> BfabricConfig:
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

    @contextmanager
    def with_auth(self, auth: BfabricAuth) -> ContextManager[Bfabric]:
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
        # NOTE: According to old interface, this is equivalent to plain=True
        results = self.engine.read(endpoint=endpoint, obj=obj, auth=self.auth, page=1, return_id_only=return_id_only)
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
        logging.info(f"Requested pages: {requested_pages}")

        # NOTE: Page numbering starts at 1
        response_items = []
        errors = results.errors
        page_offset = initial_offset
        for i_iter, i_page in enumerate(requested_pages):
            if not (i_iter == 0 and i_page == 1):
                print(f"-- reading page {i_page} of {n_available_pages}", file=sys.stderr)
                results = self.engine.read(
                    endpoint=endpoint, obj=obj, auth=self.auth, page=i_page, return_id_only=return_id_only
                )
                errors += results.errors

            response_items += results[page_offset:]
            page_offset = 0

        result = ResultContainer(response_items, total_pages_api=n_available_pages, errors=errors)
        if check:
            result.assert_success()
        return result.get_first_n_results(max_results)

    def save(self, endpoint: str, obj: dict[str, Any], check: bool = True) -> ResultContainer:
        """Saves the provided object to the specified endpoint.
        :param endpoint: the endpoint to save to, e.g. "sample"
        :param obj: the object to save
        :param check: whether to raise an error if the response is not successful
        :return a ResultContainer describing the saved object if successful
        """
        results = self.engine.save(endpoint=endpoint, obj=obj, auth=self.auth)
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
        results = self.engine.delete(endpoint=endpoint, id=id, auth=self.auth)
        if check:
            results.assert_success()
        return results

    def exists(
        self, endpoint: str, key: str, value: int | str, query: dict[str, Any] | None = None, check: bool = True
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
            endpoint=endpoint, obj={**query, key: value}, max_results=1, check=check, return_id_only=True
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

    def get_version_message(self) -> str:
        """Returns the version message as a string."""
        package_version = importlib.metadata.version("bfabric")
        year = datetime.now().year
        engine_name = self.engine.__class__.__name__
        base_url = self.config.base_url
        user_name = f"U={self._auth.login if self._auth else None}"
        return (
            f"--- bfabricPy v{package_version} ({engine_name}, {base_url}, {user_name}) ---\n"
            f"--- Copyright (C) 2014-{year} Functional Genomics Center Zurich ---"
        )

    def print_version_message(self, stderr: bool = True) -> None:
        """Prints the version message to the console.
        :param stderr: Whether to print to stderr (True, default) or stdout (False)
        """
        console = Console(stderr=stderr, highlighter=HostnameHighlighter(), theme=DEFAULT_THEME)
        console.print(self.get_version_message(), style="bright_yellow")


def get_system_auth(
    login: str = None,
    password: str = None,
    base_url: str = None,
    config_path: str = None,
    config_env: str = None,
    optional_auth: bool = True,
    verbose: bool = False,
) -> tuple[BfabricConfig, BfabricAuth]:
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

    have_config_path = config_path is not None
    if not have_config_path:
        # Get default path config file path
        config_path = Path("~/.bfabricpy.yml").expanduser()
    else:
        config_path = Path(config_path).expanduser()


    # Use the provided config data from arguments instead of the file
    if not config_path.is_file():
        if have_config_path:
            # NOTE: If user explicitly specifies a path to a wrong config file, this has to be an exception
            raise OSError(f"Explicitly specified config file does not exist: {config_path}")
        # TODO: Convert to log
        print(f"Warning: could not find the config file in the default location: {config_path}")
        config = BfabricConfig(base_url=base_url)
        auth = None if login is None and password is None else BfabricAuth(login=login, password=password)

    # Load config from file, override some of the fields with the provided ones
    else:
        config, auth = read_config(config_path, config_env=config_env)
        config = config.copy_with(base_url=base_url)
        if (login is not None) and (password is not None):
            auth = BfabricAuth(login=login, password=password)
        elif (login is None) and (password is None):
            auth = auth
        else:
            raise OSError("Must provide both username and password, or neither.")

    if not config.base_url:
        raise ValueError("base_url missing")
    if not optional_auth and (not auth or not auth.login or not auth.password):
        raise ValueError("Authentication not initialized but required")

    if verbose:
        pprint(config)

    return config, auth

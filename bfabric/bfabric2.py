#!/usr/bin/env python3
"""B-Fabric Application Interface using WSDL

The code contains classes for wrapper_creator and submitter.

Ensure that this file is available on the bfabric exec host.

Copyright (C) 2014 - 2024 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Licensed under GPL version 3

Original Authors:
  Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
  Christian Panse <cp@fgcz.ethz.ch>

BFabric V2 Authors:
  Leonardo Schwarz
  Aleksejs Fomins

History
    The python3 library first appeared in 2014.
"""
import base64
import os
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from enum import Enum
from pprint import pprint
from typing import Union, List, Optional

from rich.console import Console

from bfabric import __version__ as PACKAGE_VERSION
from bfabric.bfabric_config import BfabricAuth, BfabricConfig, read_config
from bfabric.src.cli_formatting import HostnameHighlighter, DEFAULT_THEME
from bfabric.src.engine_suds import EngineSUDS
from bfabric.src.engine_zeep import EngineZeep
from bfabric.src.errors import get_response_errors
from bfabric.src.math_helper import div_int_ceil
from bfabric.src.paginator import page_iter, BFABRIC_QUERY_LIMIT
from bfabric.src.result_container import ResultContainer, BfabricResultType


class BfabricAPIEngineType(Enum):
    SUDS = 1
    ZEEP = 2


def get_system_auth(login: str = None, password: str = None, base_url: str = None,
                    config_path: str = None, config_env: str = None, optional_auth: bool = False, verbose: bool = False):
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
        config_path = os.path.normpath(os.path.expanduser("~/.bfabricpy.yml"))

    # Use the provided config data from arguments instead of the file
    if not os.path.isfile(config_path):
        if have_config_path:
            # NOTE: If user explicitly specifies a path to a wrong config file, this has to be an exception
            raise IOError(f"Explicitly specified config file does not exist: {config_path}")
        # TODO: Convert to log
        print(f"Warning: could not find the config file in the default location: {config_path}")
        config = BfabricConfig(base_url=base_url)
        auth = BfabricAuth(login=login, password=password)

    # Load config from file, override some of the fields with the provided ones
    else:
        config, auth = read_config(config_path, config_env=config_env, optional_auth=optional_auth)
        config = config.copy_with(base_url=base_url)
        if (login is not None) and (password is not None):
            auth = BfabricAuth(login=login, password=password)
        elif (login is None) and (password is None):
            auth = auth
        else:
            raise IOError("Must provide both username and password, or neither.")

    if not config.base_url:
        raise ValueError("base_url missing")
    if not optional_auth:
        if not auth or not auth.login or not auth.password:
            raise ValueError("Authentification not initialized but required")

    if verbose:
        pprint(config)

    return config, auth


# TODO: What does idonly do for SUDS? Does it make sense for Zeep?
# TODO: What does includedeletableupdateable do for Zeep? Does it make sense for Suds?
# TODO: How to deal with save-skip fields in Zeep? Does it happen in SUDS?
class Bfabric:
    """Bfabric client class, providing general functionality for interaction with the B-Fabric API."""

    def __init__(
        self,
        config: BfabricConfig,
        auth: Optional[BfabricAuth],
        engine: BfabricAPIEngineType = BfabricAPIEngineType.SUDS,
        verbose: bool = False
    ):
        self.verbose = verbose
        self.query_counter = 0
        self._config = config
        self._auth = auth

        if engine == BfabricAPIEngineType.SUDS:
            self.engine = EngineSUDS(base_url=config.base_url)
            self.result_type = BfabricResultType.LISTSUDS
        elif engine == BfabricAPIEngineType.ZEEP:
            self.engine = EngineZeep(base_url=config.base_url)
            self.result_type = BfabricResultType.LISTZEEP
        else:
            raise ValueError(f"Unexpected engine: {engine}")

        if self.verbose:
            self.print_version_message()

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
    def with_auth(self, auth: BfabricAuth):
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

    def read(self, endpoint: str, obj: dict, max_results: Optional[int] = 100, offset: int = 0, readid: bool = False, check: bool = True,
             **kwargs) -> ResultContainer:
        """Reads objects from the specified endpoint that match all specified attributes in `obj`.
        By setting `max_results` it is possible to change the number of results that are returned.
        :param endpoint: endpoint
        :param obj: query dictionary
        :param max_results: cap on the number of results to query. The code will keep reading pages until all pages
           are read or expected number of results has been reached. If None, load all available pages.
           NOTE: max_results will be rounded upwards to the nearest multiple of BFABRIC_QUERY_LIMIT, because results
           come in blocks, and there is little overhead to providing results over integer number of pages.
        :param offset: the number of elements to skip before starting to return results (useful for pagination, default
              is 0 which means no skipping)
        :param readid: whether to use reading by ID. Currently only available for engine=SUDS
            TODO: Test the extent to which this method works. Add safeguards
        :param check: whether to check for errors in the response
        :return: List of responses, packaged in the results container
        """

        # Get the first page.
        # NOTE: According to old interface, this is equivalent to plain=True
        response = self._read_method(readid, endpoint, obj, page=1, **kwargs)

        try:
            n_available_pages = response["numberofpages"]
        except AttributeError:
            n_available_pages = 0

        # Return empty list if nothing found
        if not n_available_pages:
            result = ResultContainer([], self.result_type, total_pages_api=0, errors=get_response_errors(response, endpoint))
            if check:
                result.assert_success()
            return result

        # Get results from other pages as well, if need be
        # Only load as many pages as user has interest in
        if max_results is None:
            n_pages_trg = n_available_pages
        else:
            n_pages_trg = min(n_available_pages, div_int_ceil(max_results, BFABRIC_QUERY_LIMIT))

        # NOTE: Page numbering starts at 1
        response_items = response[endpoint]
        errors = []
        for i_page in range(2, n_pages_trg + 1):
            print('-- reading page', i_page, 'of', n_available_pages)
            response = self._read_method(readid, endpoint, obj, page=i_page, **kwargs)
            errors += get_response_errors(response, endpoint)
            response_items += response[endpoint]

        result = ResultContainer(response_items, self.result_type, total_pages_api=n_available_pages, errors=errors)
        if check:
            result.assert_success()
        return result

    def _determine_relevant_pages_and_indices(self, n_available_pages: int, max_results: Optional[int], offset: int):
        if n_available_pages == 0:
            return {"pages": [], "indices": []}
        page_size = BFABRIC_QUERY_LIMIT

        if max_results is None:
            # TODO this could contain more than the actually available items, so computing indices might be tricky
            max_results = n_available_pages * page_size




    def save(self, endpoint: str, obj: dict, check: bool = True, **kwargs) -> ResultContainer:
        results = self.engine.save(endpoint, obj, auth=self.auth, **kwargs)
        result = ResultContainer(results[endpoint], self.result_type, errors=get_response_errors(results, endpoint))
        if check:
            result.assert_success()
        return result

    def delete(self, endpoint: str, id: Union[List, int], check: bool = True) -> ResultContainer:
        results = self.engine.delete(endpoint, id, auth=self.auth)
        result = ResultContainer(results[endpoint], self.result_type, errors=get_response_errors(results, endpoint))
        if check:
            result.assert_success()
        return result

    def upload_resource(self, resource_name: str, content: bytes, workunit_id: int, check: bool = True) -> ResultContainer:
        content_encoded = base64.b64encode(content).decode()
        return self.save(
            endpoint='resource',
            obj={'base64': content_encoded,
                 'name': resource_name,
                 'description': "base64 encoded file",
                 'workunitid': workunit_id},
            check=check
        )

    def _read_method(self, readid: bool, endpoint: str, obj: dict, page: int = 1, **kwargs):
        if readid:
            # https://fgcz-bfabric.uzh.ch/wiki/tiki-index.php?page=endpoint.workunit#Web_Method_readid_
            return self.engine.readid(endpoint, obj, auth=self.auth, page=page, **kwargs)
        else:
            return self.engine.read(endpoint, obj, auth=self.auth, page=page, **kwargs)

    ############################
    # Multi-query functionality
    ############################

    # TODO: Is this scope sufficient? Is there ever more than one multi-query parameter, and/or not at the root of dict?
    def read_multi(self, endpoint: str, obj: dict, multi_query_key: str, multi_query_vals: list,
                   readid: bool = False, **kwargs) -> ResultContainer:
        """
        Makes a 1-parameter multi-query (there is 1 parameter that takes a list of values)
        Since the API only allows BFABRIC_QUERY_LIMIT queries per page, split the list into chunks before querying
        :param endpoint: endpoint
        :param obj: query dictionary
        :param multi_query_key:  key for which the multi-query is performed
        :param multi_query_vals: list of values for which the multi-query is performed
        :param readid: whether to use reading by ID. Currently only available for engine=SUDS
            TODO: Test the extent to which this method works. Add safeguards
        :return: List of responses, packaged in the results container

        NOTE: It is assumed that there is only 1 response for each value.
        """

        response_tot = ResultContainer([], self.result_type, total_pages_api = 0)
        obj_extended = deepcopy(obj)  # Make a copy of the query, not to make edits to the argument

        # Iterate over request chunks that fit into a single API page
        for page_vals in page_iter(multi_query_vals):
            obj_extended[multi_query_key] = page_vals

            # TODO: Test what happens if there are multiple responses to each of the individual queries.
            #     * What would happen?
            #     * What would happen if total number of responses would exceed 100 now?
            #     * What would happen if we naively made a multi-query with more than 100 values? Would API paginate
            #       automatically? If yes, perhaps we don't need this method at all?
            # TODO: It is assumed that a user requesting multi_query always wants all of the pages. Can anybody think of
            #   exceptions to this?
            response_this = self.read(endpoint, obj_extended, max_results=None, readid=readid, **kwargs)
            response_tot.extend(response_this)

        return response_tot

    # NOTE: Save-multi method is likely useless. When saving multiple objects, they all have different fields.
    #    One option would be to provide a dataframe, but it might struggle with nested dicts
    #    Likely best solution is to not provide this method, and let users run a for-loop themselves.
    # def save_multi(self, endpoint: str, obj_lst: list, **kwargs) -> ResultContainer:
    #     response_tot = ResultContainer([], self.result_type, total_pages_api = 0)
    #
    #     # Iterate over request chunks that fit into a single API page
    #     for page_objs in page_iter(obj_lst):
    #         response_page = self.save(endpoint, page_objs, **kwargs)
    #         response_tot.extend(response_page)
    #
    #     return response_tot

    def delete_multi(self, endpoint: str, id_list: list) -> ResultContainer:
        response_tot = ResultContainer([], self.result_type, total_pages_api=0)

        if len(id_list) == 0:
            print('Warning, empty list provided for deletion, ignoring')
            return response_tot

        # Iterate over request chunks that fit into a single API page
        for page_ids in page_iter(id_list):
            response_page = self.delete(endpoint, page_ids)
            response_tot.extend(response_page)

        return response_tot

    def exists(self, endpoint: str, key: str, value: Union[List, Union[int, str]]) -> Union[bool, List[bool]]:
        """
        :param endpoint:  endpoint
        :param key:       A key for the query (e.g. id or name)
        :param value:     A value or a list of values
        :return:          Return a single bool or a list of bools for each value
            For each value, test if a key with that value is found in the API.
        """
        is_scalar = isinstance(value, (int, str))

        # 1. Read data for this id
        if is_scalar:
            results = self.read(endpoint, {key: value})
        elif isinstance(value, list):
            results = self.read_multi(endpoint, {}, key, value)
        else:
            raise ValueError("Unexpected data type", type(value))

        # 2. Extract all the ids for which there was a response
        result_vals = []
        for r in results.results:
            if key in r:
                result_vals += [r[key]]
            elif '_' + key in r:   # TODO: Remove this if SUDS bug is ever resolved
                result_vals += [r['_' + key]]

        # 3. For each of the requested ids, return true if there was a response and false if there was not
        if is_scalar:
            return value in result_vals
        else:
            return [val in result_vals for val in value]

    def get_version_message(self) -> str:
        """Returns the version message as a string."""
        year = datetime.now().year
        engine_name = self.engine.__class__.__name__
        base_url = self.config.base_url
        user_name = f"U={self._auth.login if self._auth else None}"
        return (
            f"--- bfabricPy v{PACKAGE_VERSION} ({engine_name}, {base_url}, {user_name}) ---\n"
            f"--- Copyright (C) 2014-{year} Functional Genomics Center Zurich ---"
        )

    def print_version_message(self, stderr: bool = True) -> None:
        """Prints the version message to the console.
        :param stderr: Whether to print to stderr (True, default) or stdout (False)
        """
        console = Console(stderr=stderr, highlighter=HostnameHighlighter(), theme=DEFAULT_THEME)
        console.print(self.get_version_message(), style="bright_yellow")


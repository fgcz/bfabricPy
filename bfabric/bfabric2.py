#!/usr/bin/env python3
# -*- coding: latin1 -*-

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

import os
from enum import Enum
from copy import deepcopy
from typing import Union, List, Optional

from bfabric.src.math_helper import div_int_ceil
from bfabric.src.engine_suds import EngineSUDS
from bfabric.src.engine_zeep import EngineZeep
from bfabric.src.result_container import ResultContainer, BfabricResultType
from bfabric.bfabric_config import BfabricAuth, BfabricConfig, parse_bfabricrc_py

class BfabricAPIEngineType(Enum):
    SUDS = 1
    ZEEP = 2

# Single page query limit for BFabric API (as of time of writing, adapt if it changes)
BFABRIC_QUERY_LIMIT = 100


def get_system_auth():
    path_bfabricrc = os.path.normpath(os.path.expanduser("~/.bfabricrc.py"))
    if not os.path.isfile(path_bfabricrc):
        raise IOError("Config file not found:", path_bfabricrc)

    with open(path_bfabricrc, "r", encoding="utf-8") as file:
        config, auth = parse_bfabricrc_py(file)

    return config, auth


# TODO: What does idonly do for SUDS? Does it make sense for Zeep?
# TODO: What does includedeletableupdateable do for Zeep? Does it make sense for Suds?
# TODO: How to deal with save-skip fields in Zeep? Does it happen in SUDS?
class Bfabric(object):
    """B-Fabric python3 module
    Implements read and save object methods for B-Fabric wsdl interface
    """

    def __init__(self, config: BfabricConfig, auth: BfabricAuth,
                 engine: BfabricAPIEngineType = BfabricAPIEngineType.SUDS, verbose: bool = False):

        self.verbose = verbose
        self.query_counter = 0

        if engine == BfabricAPIEngineType.SUDS:
            self.engine = EngineSUDS(auth.login, auth.password, config.base_url)
            self.result_type = BfabricResultType.LISTSUDS
        elif engine == BfabricAPIEngineType.ZEEP:
            self.engine = EngineZeep(auth.login, auth.password, config.base_url)
            self.result_type = BfabricResultType.LISTZEEP
        else:
            raise ValueError("Unexpected engine", BfabricAPIEngineType)

    def _read_method(self, readid: bool, endpoint: str, obj: dict, page: int = 1, **kwargs):
        if readid:
            # https://fgcz-bfabric.uzh.ch/wiki/tiki-index.php?page=endpoint.workunit#Web_Method_readid_
            return self.engine.readid(endpoint, obj, page=page, **kwargs)
        else:
            return self.engine.read(endpoint, obj, page=page, **kwargs)

    def read(self, endpoint: str, obj: dict, max_results: Optional[int] = 100, readid: bool = False,
             **kwargs) -> ResultContainer:
        """
        Make a read query to the engine. Determine the number of pages. Make calls for every page, concatenate
           results.
        :param endpoint: endpoint
        :param obj: query dictionary
        :param max_results: cap on the number of results to query. The code will keep reading pages until all pages
           are read or expected number of results has been reached. If None, load all available pages.
           NOTE: max_results will be rounded upwards to the nearest multiple of BFABRIC_QUERY_LIMIT, because results
           come in blocks, and there is little overhead to providing results over integer number of pages.
        :param readid: whether to use reading by ID. Currently only available for engine=SUDS
            TODO: Test the extent to which this method works. Add safeguards
        :return: List of responses, packaged in the results container
        """

        # Get the first page.
        # NOTE: According to old interface, this is equivalent to plain=True
        response = self._read_method(readid, endpoint, obj, page=1, **kwargs)
        n_pages = response["numberofpages"]

        # Return empty list if nothing found
        if not n_pages:
            return ResultContainer([], self.result_type, total_pages_api=0)

        # Get results from other pages as well, if need be
        # Only load as many pages as user has interest in
        if max_results is None:
            n_pages_trg = n_pages
        else:
            n_pages_trg = min(n_pages, div_int_ceil(max_results, BFABRIC_QUERY_LIMIT))

        # NOTE: Page numbering starts at 1
        response_list = response[endpoint]
        for i_page in range(2, n_pages_trg + 1):
            print('-- reading page', i_page, 'of', n_pages)
            response_list += self._read_method(readid, endpoint, obj, page=i_page, **kwargs)[endpoint]

        return ResultContainer(response_list, self.result_type, total_pages_api=n_pages)

    def save(self, endpoint: str, obj: dict, **kwargs) -> ResultContainer:
        results = self.engine.save(endpoint, obj, **kwargs)
        return ResultContainer(results[endpoint], self.result_type)

    def delete(self, endpoint: str, id: Union[List, int]) -> ResultContainer:
        results = self.engine.delete(endpoint, id)
        return ResultContainer(results[endpoint], self.result_type)


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
        obj_exteded = deepcopy(obj)  # Make a copy of the query, not to make edits to the argument

        for i in range(0, len(multi_query_vals), BFABRIC_QUERY_LIMIT):
            # Limit the multi-query parameter to an acceptable chunk size
            obj_exteded[multi_query_key] = multi_query_vals[i:i + BFABRIC_QUERY_LIMIT]

            # TODO: Test what happens if there are multiple responses to each of the individual queries.
            #     * What would happen?
            #     * What would happen if total number of responses would exceed 100 now?
            #     * What would happen if we naively made a multi-query with more than 100 values? Would API paginate
            #       automatically? If yes, perhaps we don't need this method at all?
            # TODO: It is assumed that a user requesting multi_query always wants all of the pages. Can anybody think of
            #   exceptions to this?
            response_this = self.read(endpoint, obj_exteded, max_results=None, readid=readid, **kwargs)
            response_tot.append(response_this)

        return response_tot

    def save_multi(self, endpoint: str, obj_lst: list, **kwargs) -> ResultContainer:
        # We must account for the possibility that the number of query values exceeds the BFabric maximum,
        # so we must split it into smaller chunks

        response_tot = ResultContainer([], self.result_type, total_pages_api = 0)
        for i in range(0, len(obj_lst), BFABRIC_QUERY_LIMIT):
            obj_list_this = obj_lst[i:i + BFABRIC_QUERY_LIMIT]
            response_this = self.save(endpoint, obj_list_this, **kwargs)
            response_tot.append(response_this)

        return response_tot

    def delete_multi(self, endpoint: str, id_list: list) -> ResultContainer:
        response_tot = ResultContainer([], self.result_type, total_pages_api=0)

        if len(id_list) == 0:
            print('Warning, empty list provided for deletion, ignoring')
            return response_tot

        for i in range(0, len(id_list), BFABRIC_QUERY_LIMIT):
            id_list_this = id_list[i:i + BFABRIC_QUERY_LIMIT]
            response_this = self.delete(endpoint, id_list_this)
            response_tot.append(response_this)

        return response_tot

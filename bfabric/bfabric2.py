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



# TODO: Move login checks to Auth
# if login is None:
#     login = self.config.login
#
# if password is None:
#     password = self.config.password
#
# if len(login) >= 32:
#     raise ValueError("Sorry, login >= 32 characters.")
#
# if len(password) != 32:
#     raise ValueError("Sorry, password != 32 characters.")



from enum import Enum
from typing import Union, List

from bfabric.src.engine_suds import EngineSUDS
from bfabric.src.engine_zeep import EngineZeep
from bfabric.src.result_container import ResultContainer, BfabricResultType

class BfabricAPIEngineType(Enum):
    SUDS = 1
    ZEEP = 2


# TODO: What does idonly do for SUDS? Does it make sense for Zeep?
# TODO: What does includedeletableupdateable do for Zeep? Does it make sense for Suds?
# TODO: How to deal with save-skip fields in Zeep? Does it happen in SUDS?
class Bfabric(object):
    """B-Fabric python3 module
    Implements read and save object methods for B-Fabric wsdl interface
    """

    def __init__(self, auth_class, config_class, engine: BfabricAPIEngineType = BfabricAPIEngineType.SUDS,
                 verbose: bool = False):

        self.verbose = verbose
        self.query_counter = 0

        if engine == BfabricAPIEngineType.SUDS:
            self.engine = EngineSUDS(auth_class.login(), auth_class.password(), config_class.webbase())
            self.resultType = BfabricResultType.LISTSUDS
        elif engine == BfabricAPIEngineType.ZEEP:
            self.engine = EngineZeep(auth_class.login(), auth_class.password(), config_class.webbase())
            self.resultType = BfabricResultType.LISTZEEP
        else:
            raise ValueError("Unexpected engine", BfabricAPIEngineType)

    # TODO: Perform pagination. Return inner values, i.e. val[endpoint].
    def read(self, endpoint: str, obj: dict, page: int = 1, **kwargs) -> ResultContainer:
        results = self.engine.read(endpoint, obj, page = page, **kwargs)
        return ResultContainer(results, self.resultType)

    # TODO: Perform pagination. Return inner values, i.e. val[endpoint].
    def readid(self, endpoint: str, obj: dict, page: int = 1, plain: bool = False, **kwargs) -> ResultContainer:
        results = self.engine.readid(endpoint, obj, page=page, **kwargs)
        return ResultContainer(results, self.resultType)

    # TODO: Perform pagination. Return inner values, i.e. val[endpoint].
    def save(self, endpoint: str, obj: dict, **kwargs) -> ResultContainer:
        results = self.engine.save(endpoint, obj, **kwargs)
        return ResultContainer(results, self.resultType)

    # TODO: Perform pagination. Return inner values, i.e. val[endpoint].
    def delete(self, endpoint: str, id: Union[List, int]) -> ResultContainer:
        results = self.engine.delete(endpoint, id)
        return ResultContainer(results, self.resultType)

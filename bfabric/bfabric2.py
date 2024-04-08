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
from bfabric.src.result_container import ResultContainer, BFABRIC_RESULT_TYPE

class BFABRIC_API_ENGINE(Enum):
    SUDS = 1
    ZEEP = 2


# TODO: What does idonly do for SUDS? Does it make sense for Zeep?
# TODO: What does includedeletableupdateable do for Zeep? Does it make sense for Suds?
# TODO: How to deal with save-skip fields in Zeep? Does it happen in SUDS?
class Bfabric(object):
    """B-Fabric python3 module
    Implements read and save object methods for B-Fabric wsdl interface
    """

    def __init__(self, authClass, configClass, engine: BFABRIC_API_ENGINE = BFABRIC_API_ENGINE.SUDS,
                 verbose: bool = False):

        self.verbose = verbose
        self.query_counter = 0

        if engine == BFABRIC_API_ENGINE.SUDS:
            self.engine = EngineSUDS(authClass.login(), authClass.password(), configClass.webbase())
            self.resultType = BFABRIC_RESULT_TYPE.LISTSUDS
        elif engine == BFABRIC_API_ENGINE.ZEEP:
            self.engine = EngineZeep(authClass.login(), authClass.password(), configClass.webbase())
            self.resultType = BFABRIC_RESULT_TYPE.LISTZEEP
        else:
            raise ValueError("Unexpected engine", BFABRIC_API_ENGINE)

    def read(self, endpoint: str, obj: dict, page: int = 1, plain: bool = False, **kwargs) -> ResultContainer:
        results = self.engine.read(endpoint, obj, page = page, **kwargs)
        return ResultContainer(results, self.resultType)


    def readid(self, endpoint: str, obj: dict, page: int = 1, plain: bool = False, **kwargs) -> ResultContainer:
        results = self.engine.readid(endpoint, obj, page=page, **kwargs)
        return ResultContainer(results, self.resultType)

    def save(self, endpoint: str, obj: dict, **kwargs) -> ResultContainer:
        results = self.engine.save(endpoint, obj, **kwargs)
        return ResultContainer(results, self.resultType)

    def delete(self, endpoint: str, id: Union[List, int]) -> ResultContainer:
        results = self.engine.delete(endpoint, id)
        return ResultContainer(results, self.resultType)

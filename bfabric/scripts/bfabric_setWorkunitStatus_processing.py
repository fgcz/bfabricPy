#!/usr/bin/python
# -*- coding: latin1 -*-

"""
set status of a resource of a given resource id
"""

# Copyright (C) 2023 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# https://github.com/fgcz/bfabricPy/

import sys
import bfabric

from random import randint
from time import sleep

import bfabric.wrapper_creator.bfabric_feeder

if __name__ == "__main__":
    if len(sys.argv) > 1:
        B = bfabric.wrapper_creator.bfabric_feeder.BfabricFeeder()
        res = B.save_object(endpoint='workunit', obj={'id': int(sys.argv[1]), 'status': 'processing'})
        B.print_json(res)

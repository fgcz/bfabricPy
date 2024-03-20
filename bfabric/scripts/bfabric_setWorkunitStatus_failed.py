#!/usr/bin/python
# -*- coding: latin1 -*-

"""
set status of a resource of a given resource id
"""

# Copyright (C) 2021 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Christian Panse <cp@fgcz.ethz.ch>
#   Maria

# 2021-02-02

import sys
import bfabric

from random import randint
from time import sleep


if __name__ == "__main__":
    if len(sys.argv) > 1:
        bfapp = bfabric.BfabricFeeder()

        workunitid = int(sys.argv[1])
        print(f"workunitit={workunitid}")

        res = bfapp.save_object(endpoint='workunit', obj={'id': workunitid, 'status': 'failed'})
        bfapp.print_json(res)
        print ("alive")

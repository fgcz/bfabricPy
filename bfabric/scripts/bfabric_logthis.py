#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
set status of a resource of a given external job
input <externaljobid> <message>
"""

# Copyright (C) 2023 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Author:
#   Christian Panse <cp@fgcz.ethz.ch>

import sys
import bfabric

from random import randint
from time import sleep

import bfabric.wrapper_creator.bfabric_feeder

if __name__ == "__main__":
    if len(sys.argv) > 1:
        B = bfabric.wrapper_creator.bfabric_feeder.BfabricFeeder()
        try:
            externaljobid, msg = (int(sys.argv[1]), sys.argv[2])
        except:
            raise ("Usage: bfabric_logthis.py <externaljobid> <msg>")

        rv = B.save_object('externaljob', {'id': externaljobid, 'logthis': msg})
        # B.print_json(rv)

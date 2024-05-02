#!/usr/bin/python
# -*- coding: latin1 -*-

"""
set status of a resource of a given resource id
"""

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/fgcz_bfabric_setResourceStatus_available.py $
# $Id: fgcz_bfabric_setResourceStatus_available.py 2397 2016-09-06 07:04:35Z cpanse $

import sys
import bfabric

from random import randint
from time import sleep

import bfabric.wrapper_creator.bfabric_feeder

if __name__ == "__main__":
    if len(sys.argv) > 1:
        B = bfabric.wrapper_creator.bfabric_feeder.BfabricFeeder()

        res = B.save_object(endpoint='workunit', obj={'id': int(sys.argv[1]), 'status': 'available'})
        B.print_json(res)

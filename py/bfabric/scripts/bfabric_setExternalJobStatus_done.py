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
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_setExternalJobStatus_done.py $
# $Id: bfabric_setExternalJobStatus_done.py 2593 2016-11-22 10:10:06Z cpanse $

import sys
import bfabric

if __name__ == "__main__":
    bfapp = bfabric.BfabricFeeder()
    if len(sys.argv) > 1:
        for i in range(1, len(sys.argv)):
            res=bfapp.save_object('externaljob', {'id':int(sys.argv[i]), 'status':'done'})

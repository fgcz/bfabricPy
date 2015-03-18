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
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/fgcz_bfabric_setExternalJobStatus_done.py $
# $Id: fgcz_bfabric_report_resource.py 1290 2014-01-31 07:15:01Z cpanse $

import sys
import bfabric

if __name__ == "__main__":
    if len(sys.argv) > 1:
        bfapp = bfabric.BfabricFeeder(login='pfeeder')
        bfapp.set_bfabric_wsdlurl("http://fgcz-bfabric.uzh.ch/bfabric")

        for i in range(1, len(sys.argv)):
            res=bfapp.save_object('externaljob', {'id':int(sys.argv[i]), 'status':'done'})

#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
set status of a resource of a given resource id
"""

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#   Maria d'Errico <maria.derrico@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_setExternalJobStatus_done.py $
# $Id: bfabric_setExternalJobStatus_done.py 2996 2017-08-18 12:11:17Z cpanse $

import sys
import bfabric
import bfabric.wrapper_creator.bfabric_feeder

if __name__ == "__main__":
    bfapp = bfabric.wrapper_creator.bfabric_feeder.BfabricFeeder()

    if len(sys.argv) > 1:
        for i in range(1, len(sys.argv)):
            try:
                res = bfapp.save_object('externaljob', {'id':int(sys.argv[i]), 'status':'done'})
                print(res)
            except:
                print("failed to set externaljob with id={} 'available'.".format(int(sys.argv[i])))
                raise

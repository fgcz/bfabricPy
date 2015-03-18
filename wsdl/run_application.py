#!/usr/bin/python
# -*- coding: latin1 -*-

"""
"""

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/run_application.py $
# $Id: wrapper_creator.py 1289 2014-01-31 06:49:24Z cpanse $ 

import os
import sys
import base64
import bfabric
import datetime

if __name__ == "__main__":
    #if len(sys.argv) == 3 and sys.argv[1] == '-j' and int(sys.argv[2]) > 0:
    #    externaljobid = int(sys.argv[2])
    #else:
    #    print "usage: " + sys.argv[0] + " -j <externaljobid>"    
    #    sys.exit(1)

    bfapp = bfabric.Bfabric(login='pfeeder')

    res = bfapp.save_object('workunit', {'projectid': 403,
        'name': 'CP cmd test application run',
        'applicationid': 152,
        'status': 'running',
        'inputresourceid': [144056, 144057]})

    print res

#!/usr/bin/python
# -*- coding: latin1 -*-

"""
A wrapper_creator for B-Fabric
Gets an external job id from B-Fabric
Creates an executable for the submitter

after successfull uploading the executables the wrapper creator creates an
externaljob
"""

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn/repos/scripts/trunk/linux/bfabric/apps/python/wrapper_creator.py $
# $Id: wrapper_creator.py 1289 2014-01-31 06:49:24Z cpanse $ 

import os
import sys
#sys.path.insert(0, '/export/bfabric/bfabric/.python')
import bfabric
import datetime

import fileinput

if __name__ == "__main__":
    bfapp = bfabric.Bfabric(login='pfeeder')
    bfapp.set_bfabric_webbase("http://fgcz-bfabric.uzh.ch/bfabric")


    for line in fileinput.input():
        workunitid = int(line)
        assert isinstance(workunitid, int)
        res = bfapp.delete_object(endpoint='workunit', id=workunitid)
        print res
    sys.exit(0)

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
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/fgcz_bfabric_get_resource_by_workunitid.py $
# $Id: fgcz_bfabric_get_resource_by_workunitid.py 2628 2017-02-03 08:12:47Z cpanse $ 

import os
import sys
sys.path.insert(0, '/home//bfabric/.python')
import bfabric
import datetime

if __name__ == "__main__":
    bfapp = bfabric.Bfabric(login='pfeeder')

    workunit = bfapp.read_object(endpoint='workunit', obj={'id': sys.argv[1]})
    for i in workunit[0].resource:
        resource = bfapp.read_object(endpoint='resource', obj={'id': i._id})
        print resource[0].relativepath
    sys.exit(0)

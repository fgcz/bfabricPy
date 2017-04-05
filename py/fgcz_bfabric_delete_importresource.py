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
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/fgcz_bfabric_delete_importresource.py $
# $Id: fgcz_bfabric_delete_importresource.py 2628 2017-02-03 08:12:47Z cpanse $ 

import os
import sys
sys.path.insert(0, '/home//bfabric/.python')
import bfabric
import datetime

if __name__ == "__main__":
    bfapp = bfabric.Bfabric(login='pfeeder')

    workunit = bfapp.delete_object(endpoint='importresource', id=sys.argv[1])
    print workunit
    sys.exit(0)

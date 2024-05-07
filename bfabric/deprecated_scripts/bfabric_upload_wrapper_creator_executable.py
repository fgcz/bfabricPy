#!/usr/bin/python
# -*- coding: latin1 -*-

"""
Uploader for B-Fabric
"""

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_upload_wrapper_creator_executable.py $
# $Id: bfabric_upload_wrapper_creator_executable.py 2478 2016-09-26 09:46:53Z cpanse $ 


import os
import sys
import base64
from bfabric import Bfabric

if __name__ == "__main__":
    executeableFileName = "wrapper_creator_yaml.py"
    if not os.path.isfile(executeableFileName):
        print "could not fine '{}'.".format(executeableFileName)
        sys.exit(1)

    bfapp = Bfabric()
    with open(executeableFileName, 'r') as f:
        executable = f.read()

    attr = { 'name': 'yaml 004', 
        'context': 'WRAPPERCREATOR', 
        'parameter': None, 
        'description': 'None.', 
        'masterexecutableid': 11851,
        'base64': base64.b64encode(executable) }

    res = bfapp.save_object('executable', attr)

    print (res)

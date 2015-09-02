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
# $HeadURL: http://fgcz-svn/repos/scripts/trunk/linux/bfabric/apps/python/upload_wrapper_creator_executable.py $
# $Id: upload_wrapper_creator_executable.py 1938 2015-09-01 09:33:04Z cpanse $ 


import os
import sys
import base64
import bfabric

import getpass

if __name__ == "__main__":
    executeableFileName="wrapper_creator_yaml.py"

    bfapp = bfabric.Bfabric(login='pfeeder')
    bfapp.set_bfabric_webbase("http://fgcz-bfabric.uzh.ch/bfabric")


    with open(executeableFileName, 'r') as f:
        executable = f.read()

    pw = getpass.getpass()
    bfapp.set_bfabric_credentials('cpanse', pw)

    #attr = { 'name': 'PRX qsub wrapper_creator version 17 input resource ids.', 
    attr = { 'name': 'yaml 003', 
        'context': 'WRAPPERCREATOR', 
        'parameter': None, 
        'description': 'None.', 
        'masterexecutableid': 11851,
        'base64': base64.b64encode(executable) }

    res = bfapp.save_object('executable', attr)
    print (res)

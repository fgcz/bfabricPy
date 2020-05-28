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

# @Version: $Rev: 1232 $


import os
import sys
import base64
from bfabric import Bfabric

SVN="$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_upload_submitter_executable.py $"

if __name__ == "__main__":
    if len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
        executeableFileName = sys.argv[1]
    else:
        print("usage: " + sys.argv[0] + "<filename>")    
        sys.exit(1)

    bfapp = Bfabric()

    with open(executeableFileName, 'r') as f:
        executable = f.read()

    attr = { 'name': 'yaml /  Grid Engine executable', 
        'context': 'SUBMITTER', 
        'parameter': {'modifiable': 'true', 
            'description': 'which Grid Engine queue should be used.', 
            'key': 'queue', 
            'label': 'queue', 
            'required': 'true', 
            'type':'string', 
            'value': 'PRX@fgcz-r-028'}, 
        'description': 'stages yaml config file to an appliaction using Grid Eninge .', 'version': 3.00, 
        'masterexecutableid': 11871, 
        'base64': base64.b64encode(executable) }

    res = bfapp.save_object('executable', attr)

    print (res)

#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""

Copyright (C) 2017 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_upload_resource.py $
$Id: bfabric_upload_resource.py 2989 2017-08-17 12:58:53Z cpanse $ 



this script takes a blob file and a workunit id as input and adds the file as resource to bfabric
"""


import os
import sys
import base64
from bfabric import Bfabric

if __name__ == "__main__":

    filename = sys.argv[1]
    wuid = sys.argv[2]

    with open(filename, 'rb') as f:
        content = f.read()

    try:
        resource_base64 = base64.b64encode(content).decode()
    except:
        print("error: could not encode content")
        raise

    B = Bfabric()
    res = B.save_object('resource', {'base64': resource_base64, 'name': os.path.basename(filename), 'workunitid': wuid})
    B.print_json(res)

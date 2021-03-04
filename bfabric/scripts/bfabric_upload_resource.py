#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""

Copyright (C) 2017,2020 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

this script takes a blob file and a workunit id as input and adds the file as resource to bfabric
"""

import sys
import os
from bfabric import Bfabric

if __name__ == "__main__":
    if len(sys.argv) == 3 and os.path.isfile(sys.argv[1]):
        B = Bfabric()
        B.print_json(B.upload_file(filename = sys.argv[1], workunitid = int(sys.argv[2])))
    else:
        print("usage:\nbfabric_upload_resource.py <filename> <workunitid>")
        sys.exit(1)

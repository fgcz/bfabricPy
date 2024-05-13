#!/usr/bin/python
# -*- coding: latin1 -*-

"""

Copyright (C) 2016 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_save_workunit.py $
$Id: bfabric_save_workunit.py 2956 2017-08-09 07:14:59Z cpanse $ 

"""

import os
import sys
import bfabric
import datetime

import bfabric.bfabric_legacy

if __name__ == "__main__":
    bfapp = bfabric.bfabric_legacy.BfabricLegacy()

    workunit = bfapp.save_object(
        endpoint="workunit",
        obj={"name": "MaxQuant report", "projectid": "1000", "applicationid": 217, "status": "available"},
    )
    print(workunit)

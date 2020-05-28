#!/usr/bin/python
# -*- coding: latin1 -*-

# $Id: bfabric_save_resource_description.py 2965M 2017-09-25 19:03:07Z (local) $
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_save_resource_description.py $
# $Date: 2017-09-25 21:03:07 +0200 (Mon, 25 Sep 2017) $


import os
import re
import time
import sys
from bfabric import Bfabric

 
################################################################################
if __name__ == "__main__":


    description = sys.stdin.readlines()

    bfapp = Bfabric()

    obj = { 'id': 264412,
            'description': ""
    }

    res = bfapp.save_object(endpoint='resource', obj=obj)
    print(res)

#!/usr/bin/python
# -*- coding: latin1 -*-

"""
Submitter for B-Fabric
"""

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmid <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn/repos/scripts/trunk/linux/bfabric/apps/python/get_executable.py $
# $Id: get_executable.py 2397 2016-09-06 07:04:35Z cpanse $ 

# @name: submitter_OpenGridSceduler
# @description: this script submitts to the open grid sceduler
# @context: SUBMITTER
# @oarameter: string,q,bfabric,true,true,queue,this is a queue
# @version: $Rev: 1232 $

import os
import sys
import base64
import bfabric

if __name__ == "__main__":
    externaljobid = -1

    if len(sys.argv) == 3 and sys.argv[1] == '-id' and int(sys.argv[2]) > 0:
        executable_id = int(sys.argv[2])
    else:
        print "usage: " + sys.argv[0] + " -id <executable_id>"    
        sys.exit(1)

    bfapp = bfabric.BfabricSubmitter(login='pfeeder', externaljobid=externaljobid)

    executable = bfapp.read_object(endpoint='executable', obj={'id': executable_id})[0]

    print (base64.b64decode(executable.base64))


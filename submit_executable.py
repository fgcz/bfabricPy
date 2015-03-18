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
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/submit_executable.py $
# $Id: submit_executable.py 1289 2014-01-31 06:49:24Z cpanse $ 

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

    if len(sys.argv) == 3 and sys.argv[1] == '-j' and int(sys.argv[2]) > 0:
        externaljobid = int(sys.argv[2])
    else:
        print "usage: " + sys.argv[0] + "-j <externaljobid>"    
        sys.exit(1)

    bfapp = bfabric.BfabricSubmitter(login='pfeeder', externaljobid=externaljobid)
    bfapp.set_bfabric_wsdlurl("http://fgcz-bfabric.uzh.ch/bfabric")

    for executable in bfapp.get_executable_of_externaljobid():
        filename = "/tmp/externaljobid-" + str(externaljobid) + "_executableid-" + str(executable._id) + ".bash"

        bfapp.logger("executable = " + str(executable))

        with open(filename, 'w') as f:
            f.write(base64.b64decode(executable.base64))

        bfapp.submit(filename)

    res = bfapp.save_object(endpoint='externaljob', obj={'id':externaljobid, 'status':'done'})

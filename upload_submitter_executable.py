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
import bfabric
import getpass

SVN="$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/upload_submitter_executable.py $"

def read_bfabricrc():
    try:
        with open(os.environ['HOME']+"/.bfabricrc.py") as myfile: 
            for line in myfile:
                return(line.strip())
    except:
        return(-1)


if __name__ == "__main__":
    if len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
        executeableFileName = sys.argv[1]
    else:
        print "usage: " + sys.argv[0] + "<filename>"    
        sys.exit(1)

    bfapp = bfabric.Bfabric()
    bfapp.set_bfabric_credentials('pfeeder', read_bfabricrc())
    bfapp.set_bfabric_wsdlurl('http://fgcz-bfabric.uzh.ch/bfabric/')

    with open(executeableFileName, 'r') as f:
        executable = f.read()

    attr = { 'name': 'submitter_OpenGridSceduler', 'context': 'SUBMITTER', 'parameter': None, 
        'description': 'this script submitts to the open grid sceduler', 'version': None, 
        'masterexecutableid': 69, 
        'base64': base64.b64encode(executable) }
    res = bfapp.save_object('executable', attr)
    print (res)

    bfapp.set_bfabric_wsdlurl("http://fgcz-bfabric.uzh.ch/bfabric")
    pw = getpass.getpass()
    bfapp.set_bfabric_credentials('cpanse', pw)

    attr = { 'name': 'submitter_OpenGridSceduler', 'context': 'SUBMITTER', 'parameter': None, 
        'description': 'this script submitts to the open grid sceduler', 'version': None, 
        'masterexecutableid': 69, 
        'base64': base64.b64encode(executable) }
    res = bfapp.save_object('executable', attr)
    print (res)

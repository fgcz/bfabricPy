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
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/upload_wrapper_creator_executable.py $
# $Id: upload_wrapper_creator_executable.py 1289 2014-01-31 06:49:24Z cpanse $ 


import os
import sys
import base64
import bfabric

import getpass

if __name__ == "__main__":
    if len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
        executeableFileName = sys.argv[1]
    elif os.path.isfile('wrapper_creator2.py'):
        print "use 'wrapper_creator.py' in this directory."
        executeableFileName = 'wrapper_creator.py'
    else:
        print "usage: " + sys.argv[0] + "<filename>"    
        sys.exit(1)



    bfapp = bfabric.Bfabric(login='pfeeder')
    bfapp.set_bfabric_wsdlurl("http://fgcz-bfabric.uzh.ch/bfabric")


    with open(executeableFileName, 'r') as f:
        executable = f.read()

    """
    todo just parse the header and use the paresed attributes
    """
    attr = { 'name': 'PRX qsub wrapper_creator version 06', 
        'context': 'WRAPPERCREATOR', 
        'parameter': None, 
        'description': 'this one is working; problems with the resource weburl are not solved.', 
        'masterexecutableid': 4413,
        'base64': base64.b64encode(executable) }

    res = bfapp.save_object('executable', attr)
    print (res)

    bfapp.set_bfabric_wsdlurl("http://fgcz-bfabric.uzh.ch/bfabric")
    pw = getpass.getpass()
    bfapp.set_bfabric_credentials('cpanse', pw)

    attr = { 'name': 'PRX qsub wrapper_creator version 06', 
        'context': 'WRAPPERCREATOR', 
        'parameter': None, 
        'description': 'this one is working; problems with the resource weburl are not solved.', 
        'masterexecutableid': 11851,
        'base64': base64.b64encode(executable) }

    res = bfapp.save_object('executable', attr)
    print (res)

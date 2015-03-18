#!/usr/bin/python
# -*- coding: latin1 -*-

"""
A wrapper_creator for B-Fabric
"""

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmid <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/login.py $
# $Id: login.py 1289 2014-01-31 06:49:24Z cpanse $ 

import os
import sys
import base64
import bfabric
import datetime

SVN="$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/login.py $"

def read_bfabricrc():
    try:
        with open(os.environ['HOME']+"/.bfabricrc.py") as myfile: 
            for line in myfile:
                return(line.strip())
    except:
        return(-1)


if __name__ == "__main__":

    bfapp = bfabric.Bfabric()
    bfapp.set_bfabric_credentials('bfabricro', 'BF4by;c,712')
    # bfapp.set_bfabric_credentials('pfeeder', read_bfabricrc())
    bfapp.set_bfabric_wsdlurl('http://fgcz-bfabric.uzh.ch/bfabric/')

    workunit=bfapp.read_object(endpoint='workunit', obj={'id': 121798})
    print workunit

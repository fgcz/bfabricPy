#!/usr/bin/env python3

"""
A wrapper_creator for B-Fabric


this code generates a yaml configuaration file

example

wrapper_creator_yaml.py -j 45631

"""

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn/repos/scripts/trunk/linux/bfabric/apps/python/wrapper_creator_yaml.py $
# $Id: wrapper_creator_yaml.py 2397 2016-09-06 07:04:35Z cpanse $

import sys
from bfabric import BfabricWrapperCreator

if __name__ == "__main__":
    externaljobid = -1

    if len(sys.argv) == 3 and sys.argv[1] == "-j" and int(sys.argv[2]) > 0:
        externaljobid = int(sys.argv[2])
    else:
        print("usage: " + sys.argv[0] + " -j <externaljobid>")
        sys.exit(1)

    bfapp = BfabricWrapperCreator(externaljobid=externaljobid)

    bfapp.write_yaml()

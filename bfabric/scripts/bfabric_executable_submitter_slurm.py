#!/usr/bin/env python3 
# -*- coding: latin1 -*-

"""
Submitter for B-Fabric
"""

# Copyright (C) 2014,2015 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmid <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn/repos/scripts/trunk/linux/bfabric/apps/python/submit_executable.py $
# $Id: submit_executable.py 2397 2016-09-06 07:04:35Z cpanse $ 

# @name: submitter_OpenGridSceduler
# @description: this script submits to the open grid scheduler
# @context: SUBMITTER
# @oarameter: string, q, bfabric,true,true,queue,this is a queue
# @version: $Rev: 1232 $

"""
this is the submitter executable


example:

python submit_executable.py -j 45864
"""


#import os
#import sys
from optparse import OptionParser
from bfabric import BfabricSubmitter

def main():

    parser = OptionParser(usage="usage: %prog -j <externaljobid>",
                          version="%prog 1.0")

    parser.add_option("-j", "--externaljobid",
                      type='int',
                      action="store",
                      dest="externaljobid",
                      default=None,
                      help="external job id is required.")

    (options, args) = parser.parse_args()

    if not options.externaljobid:
        parser.error("option '-j' is required.")

    bfapp = BfabricSubmitter(externaljobid=options.externaljobid)

    bfapp.submitter_yaml()
    # TODO(cp): fix that
    # print(bfapp.query_counter)

if __name__ == "__main__":
    main()

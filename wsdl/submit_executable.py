#!/usr/bin/python 
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
# $Id: submit_executable.py 1946 2015-09-02 10:57:46Z cpanse $ 

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
import bfabric
from optparse import OptionParser



def main():

    parser = OptionParser(usage="usage: %prog -j <externaljobid> -j <queue>",
                          version="%prog 1.0")

    parser.add_option("-j", "--externaljobid",
                      type='int',
                      action="store",
                      dest="externaljobid",
                      default=None,
                      help="external job id is required.")

    parser.add_option("-q", "--queue",
                      type='string',
                      action="store",  # optional because action defaults to "store"
                      dest="queue",
                      default="PRX@fgcz-c-071",
                      help="defines Open Grid Scheduler queue name.")

    (options, args) = parser.parse_args()

    if not options.externaljobid:
        parser.error("option '-j' is required.")

    bfapp = bfabric.BfabricSubmitter(login='pfeeder',
                                     externaljobid=options.externaljobid,
                                     queue=options.queue)

    bfapp.submitter_yaml()

if __name__ == "__main__":
    main()

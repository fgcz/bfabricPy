#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
Copyright (C) 2022 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3


2022-06-03 add sample.name

Usage example:
  bfabric_read_samples_of_workunit.py 278175 
"""

import signal
import sys
import time
import bfabric


def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def print_color_msg(msg, color="93"):
    msg = "\033[{color}m--- {} ---\033[0m\n".format(msg, color=color)
    sys.stderr.write(msg)

def usage():
    print("usage:\n")
    msg = "\t{} <datasetid>".format(sys.argv[0])
    print(msg)


if __name__ == "__main__":


    try:
        if len(sys.argv) == 2:
            workunitid = sys.argv[1]
    except:
        raise

    B = bfabric.Bfabric(verbose=False)
    sys.stderr.write(bfabric.msg)

    start_time = time.time()

    res = B.read_object(endpoint="workunit", obj={'id': workunitid})

    inputresources = list(map(lambda x: B.read_object(endpoint="resource", obj={'id': x._id})[0], res[0].inputresource))

    inputresourcesname = list(map(lambda x: (x._id, x.name), inputresources))

    samples = list(map(lambda x: B.read_object(endpoint="sample", obj={'id': x.sample._id})[0], inputresources))


    # no x.groupingvar.name defined
    try:
        groupingvars = list(map(lambda x: (x._id, x.name, x.groupingvar.name), samples))
    except:
        groupingvars = list(map(lambda x: (x._id, x.name, "NA"), samples))


    print ("{}\t{}\t{}\t{}\t{}".format('workunit.id', 'inputresource.id', 'inputresource.name', 'sample.name', 'groupingvar.name'))
    for i in zip(inputresourcesname, groupingvars):
        print ("{}\t{}\t{}\t{}\t{}".format(workunitid, i[0][0], i[0][1], i[1][1], i[1][2]))

    end_time = time.time()
    print_color_msg("query time = {} seconds".format(round(end_time - start_time, 2)))

    sys.exit(0)

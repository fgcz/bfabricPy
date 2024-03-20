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
    msg = f"\x1b[{color}m--- {msg} ---\x1b[0m\n"
    sys.stderr.write(msg)

def usage():
    print("usage:\n")
    msg = f"\t{sys.argv[0]} <datasetid>"
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


    print ("workunit.id\tinputresource.id\tinputresource.name\tsample.name\tgroupingvar.name")
    for i in zip(inputresourcesname, groupingvars):
        print (f"{workunitid}\t{i[0][0]}\t{i[0][1]}\t{i[1][1]}\t{i[1][2]}")

    end_time = time.time()
    print_color_msg(f"query time = {round(end_time - start_time, 2)} seconds")

    sys.exit(0)

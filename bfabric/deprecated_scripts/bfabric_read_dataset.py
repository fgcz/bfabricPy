#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
Copyright (C) 2020 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

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


def dataset2csv(ds, sep="\t"):
    print (type(ds.attribute))

    # print header
    print (sep.join(map(lambda x: x.name, ds.attribute)))
    # print values
    for i in ds.item:
        print(sep.join(map(lambda x: x.value, i.field)))

if __name__ == "__main__":
    bfapp = bfabric.Bfabric(verbose=False)

    sys.stderr.write(bfabric.msg)

    query_obj = {}
    endpoint = "dataset"


    if len(sys.argv) == 2:
        datasetid = sys.argv[1]

    start_time = time.time()
    query_obj = {'id': '32003'}
    print_color_msg("query = {}".format(query_obj))
    res = bfapp.read_object(endpoint=endpoint, obj=query_obj)

    dataset2csv(res[0])

    end_time = time.time()
    print_color_msg("query time = {} seconds".format(round(end_time - start_time, 2)))

    sys.exit(0)

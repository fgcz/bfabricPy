#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
Copyright (C) 2014, 2019 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_list.py $
$Id: bfabric_list.py 2541M 2017-08-21 13:06:30Z (local) $ 


http://fgcz-bfabric.uzh.ch/bfabric/executable?wsdl
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
    msg = "\t{} <endpoint> <attribute> <value>".format(sys.argv[0])
    print(msg)
    msg = "\t{} <endpoint>\n\n".format(sys.argv[0])
    print(msg)
    print(("valid endpoints are: [{}]\n\n".format(",\n\t ".join(bfabric.endpoints))))
    print("example:")
    msg = "\t{} user login cpanse\n\n".format(sys.argv[0])
    print(msg)

if __name__ == "__main__":
    bfapp = bfabric.Bfabric(verbose=False)

    sys.stderr.write(bfabric.msg)

    query_obj = {}
    
    try:
        endpoint = sys.argv[1]
    except:
        usage()
        sys.exit(1)

    if len(sys.argv) == 4:
        attribute = sys.argv[2]
        name = sys.argv[3]
        query_obj[attribute] = name

    if endpoint in bfabric.endpoints:
        start_time = time.time()
        print_color_msg("query = {}".format(query_obj))
        res = bfapp.read_object(endpoint=endpoint, obj=query_obj)
        end_time = time.time()

        if res is None:
            print_color_msg("Empty result set or invalid query.", color=95)
            sys.exit(0)

        try:
            res = sorted(res, key=lambda x: x._id)
        except:
            print_color_msg("sorting failed.")

        try:
            if len(res) < 2:
                for i in res:
                    print (i)
        except Exception as e:
            print_color_msg("invalid query. {}.".format(e), color=95)
            sys.exit(1)

        try:

            print_color_msg("possible attributes are: {}.".format((", ".join([at[0] for at in res[0]]))))

            
            for x in res:
                try:
                    print(("{}\t{}\t{}\t{}".format(x._id, x.createdby, x.modified, x.name)))
                except Exception as e:
                    print(("{}\t{}\t{}".format(x._id, x.createdby, x.modified)))


        except Exception as e:
            print_color_msg("Exception: {}".format(e))
            print (res)
    else:
        print_color_msg ("The first argument must be a valid endpoint.", color=95)
        usage()
        sys.exit(1)
        

    try:
        print_color_msg("number of query result items = {}".format(len(res)))
    except:
        pass

    print_color_msg("query time = {} seconds".format(round(end_time - start_time, 2)))

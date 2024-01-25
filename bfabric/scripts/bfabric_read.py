#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""B-Fabric command line reader

Copyright:
    2014, 2019, 2024 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
    Christian Panse <cp@fgcz.ethz.ch>

License:
    GPL version 3

See also:
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

def print_color_msg(msg, color = "93"):
    sys.stderr.write(f"\033[{color}m--- {msg} ---\033[0m\n")

def usage():
    print(__doc__)
    print("usage:\n")
    msg = f"\t{sys.argv[0]} <endpoint> <attribute> <value>"
    print(msg)
    msg = "\t{} <endpoint>\n\n".format(sys.argv[0])
    print(msg)
    print("valid endpoints are: [{}]\n\n".format(",\n\t ".join(bfabric.endpoints)))
    print("example:")
    msg = "\t{} user login cpanse\n\n".format(sys.argv[0])
    print(msg)

if __name__ == "__main__":
    B = bfabric.Bfabric(verbose=False)

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
        print_color_msg(f"query = {query_obj}")
        start_time = time.time()
        res = B.read_object(endpoint = endpoint, obj = query_obj)
        end_time = time.time()

        if res is None:
            print_color_msg("Empty result set or invalid query.", color=95)
            sys.exit(0)

        try:
            res = sorted(res, key=lambda x: x._id)
        except:
            print_color_msg("sorting failed.")

        try:
            # print json object
            if len(res) < 2:
                print(res[0])
        except Exception as e:
            print_color_msg(f"invalid query. {e}.", color=95)
            sys.exit(1)

        try:
            print_color_msg("possible attributes are: {}.".format((", ".join([at[0] for at in res[0]]))))
        except Exception as e:
            print_color_msg(f"Exception: {e}")
            
        for x in res:
            try:
                print(f"{x._id}\t{x.createdby}\t{x.modified}\t{x.name}\t{x.groupingvar.name}")
            except Exception as e:
                print(f"{x._id}\t{x.createdby}\t{x.modified}")


    else:
        print_color_msg("The first argument must be a valid endpoint.", color=95)
        usage()
        sys.exit(1) 

    try:
        print_color_msg(f"number of query result items = {len(res)}")
    except:
        pass

    print_color_msg(f"query time = {round(end_time - start_time, 2)} seconds")

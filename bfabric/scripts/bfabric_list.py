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

endpoints = ['access', 'annotation', 'application',
        'attachement', 'comment', 'dataset', 'executable',
        'externaljob', 'groupingvar', 'importresource', 'mail',
        'parameter', 'project', 'resource', 'sample',
        'storage', 'user', 'workunit', 'order', 'instrument']


def usage():
    print("usage:\n")
    msg = "{} <endpoint> <attribute> <value>\n\n".format(sys.argv[0])
    print(msg)
    print("endpoint = {}\n\n".format(endpoints))
    print("example")
    msg = "{} user login cpanse\n\n".format(sys.argv[0])
    print(msg)

if __name__ == "__main__":
    bfapp = bfabric.Bfabric(verbose=False)

    msg = "\033[93m{} version {} (2019-05-21) -- \"{}\"\
        \nCopyright (C) 2019 Functional Genomics Center Zurich\033[0m\n\n"\
        .format(bfabric.name, bfabric.version, bfabric.alias)

    sys.stderr.write(msg)

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

    if endpoint in endpoints:
        start_time = time.time()
        res = bfapp.read_object(endpoint=endpoint, obj=query_obj)
        end_time = time.time()
        if len(res) == 1:
            for i in res:
                print (i)
        try:
            for x in res:
                print ("{}\t{}\t{}\t{}".format(x.id, x.createdby, x.modified, x.name))
        except:
            print (res)
    else:
        print ("The first argument must be a valid endpoint.\n")
        usage()
        sys.exit(1)
        

    try:
        msg = "\033[93m--- number of query result items = {} ---\033[0m\n".format(len(res))
        sys.stderr.write(msg)
    except:
        pass
    msg = "\033[93m--- query time = {} seconds ---\033[0m\n\n".format(end_time - start_time)
    sys.stderr.write(msg)


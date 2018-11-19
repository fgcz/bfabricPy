#!/usr/bin/env python
# -*- coding: latin1 -*-

"""

Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_list.py $
$Id: bfabric_list.py 2541M 2017-08-21 13:06:30Z (local) $ 



http://fgcz-bfabric.uzh.ch/bfabric/executable?wsdl

"""

import signal
import sys
from bfabric import Bfabric

def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    bfapp = Bfabric()

    endpoints = ['access', 'annotation', 'application',
        'attachement', 'comment', 'dataset', 'executable',
        'externaljob', 'groupingvar', 'importresource', 'mail',
        'parameter', 'project', 'resource', 'sample',
        'storage', 'user', 'workunit', 'order', 'instrument']
    query_obj = {}
    
    print len(sys.argv)

    endpoint = sys.argv[1]

    if len(sys.argv) == 4:
        attribute = sys.argv[2]
        name = sys.argv[3]
        query_obj[attribute] = name

    if endpoint in endpoints:
        res = bfapp.read_object(endpoint=endpoint, obj=query_obj)
        if len(res) == 1:
            for i in res:
                print i
        try:
            map(lambda x: sys.stdout.write("{}\t{}\t{}\t{}\n"
               .format(x._id, x.createdby, x.modified, x.name)), res)
        except:
            print res
    else:
        raise "1st argument must be a valid endpoint."


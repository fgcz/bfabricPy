#!/usr/bin/env python
# -*- coding: latin1 -*-

"""

Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_list.py $
$Id: bfabric_list.py 2541 2016-10-26 07:11:54Z cpanse $ 



http://fgcz-bfabric.uzh.ch/bfabric/executable?wsdl

"""

import sys
from bfabric import Bfabric

if __name__ == "__main__":
    bfapp = Bfabric()

    endpoints = ['access', 'annotation', 'application',
        'attachement', 'comment', 'dataset', 'executable',
        'externaljob', 'extract', 'importresource', 'mail',
        'parameter', 'project', 'resource', 'sample',
        'storage', 'user', 'workunit']
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


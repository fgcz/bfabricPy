#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""

Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_delete.py $
$Id: bfabric_delete.py 2525 2016-10-17 09:52:59Z cpanse $ 



http://fgcz-bfabric.uzh.ch/bfabric/executable?wsdl

"""

import sys
import bfabric 

if __name__ == "__main__":
    bfapp = bfabric.Bfabric()

    query_obj = {}
    
    print (len(sys.argv))

    endpoint = sys.argv[1]

    if len(sys.argv) == 3:
        id = sys.argv[2]

    if endpoint in bfabric.endpoints:
        res = bfapp.delete_object(endpoint=endpoint, id=id)
        for i in res:
            print (i)
    else:
        raise "1st argument must be a valid endpoint."


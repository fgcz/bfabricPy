#!/usr/bin/env python
# -*- coding: latin1 -*-

"""

Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_list_executables.py $
$Id: bfabric_list_executables.py 2482 2016-09-26 15:51:55Z cpanse $ 



http://fgcz-bfabric.uzh.ch/bfabric/executable?wsdl

"""

import sys
from bfabric import Bfabric

if __name__ == "__main__":
    bfapp = Bfabric()
    res = bfapp.read_object(endpoint='executable', obj={})
    map(lambda x: sys.stdout.write("{}\t{}\t{}\t{}\t{}\n"
        .format(x._id, x.createdby, x.modified, x.context, x.name)), res)

#!/usr/bin/env python
# -*- coding: latin1 -*-

"""

Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_list_pending_workunits.py $
$Id: bfabric_list_pending_workunits.py 2460 2016-09-23 14:51:01Z cpanse $ 

"""

import sys
from bfabric import Bfabric

if __name__ == "__main__":
    bfapp = Bfabric()
    workunit = bfapp.read_object(endpoint='workunit', obj={'status': 'pending'})
    map(lambda x: sys.stdout.write("{0}\t{1}\t{2}\n".format(x._id, x.createdby, x.modified)), workunit)

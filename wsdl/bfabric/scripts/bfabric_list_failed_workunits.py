#!/usr/bin/python
# -*- coding: latin1 -*-

"""

Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
  Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_list_failed_workunits.py $
$Id: bfabric_list_failed_workunits.py 2475 2016-09-26 09:02:07Z cpanse $ 

"""

import sys
from bfabric import Bfabric

if __name__ == "__main__":
    bfapp = Bfabric()
    workunit = bfapp.read_object(endpoint='workunit', obj={'status': 'failed'})
    map(lambda x: sys.stdout.write("{0}\t{1}\t{2}\n".format(x._id, x.createdby, x.modified)), workunit)

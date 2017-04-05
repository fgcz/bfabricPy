#!/usr/bin/python
# -*- coding: latin1 -*-

"""

Copyright (C) 2016 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/fgcz_bfabric_create_WU.py $
$Id: fgcz_bfabric_create_WU.py 2397 2016-09-06 07:04:35Z cpanse $ 

"""

import os
import sys
sys.path.insert(0, '/export/bfabric/bfabric/.python')
import bfabric
import datetime


if __name__ == "__main__":
    bfapp = bfabric.Bfabric(login='pfeeder')
    bfapp.set_bfabric_webbase("http://fgcz-bfabric.uzh.ch/bfabric")


    workunit = bfapp.save_object(endpoint='workunit', obj={'name': 'FCC', 'projectid': '1000', 'applicationid': 208, 'status': 'pending'})
    print (workunit)
    #map(lambda x: sys.stdout.write("{0}\t{1}\t{2}\n".format(x._id, x.createdby, x.modified)), workunit)
    #sys.exit(0)

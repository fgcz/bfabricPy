#!/usr/bin/python
# -*- coding: latin1 -*-

"""

Copyright (C) 2016 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn/repos/scripts/trunk/linux/bfabric/apps/python/fgcz_bfabric_add_RData_resources.py $
$Id: fgcz_bfabric_add_RData_resources.py 2397 2016-09-06 07:04:35Z cpanse $ 


this script adds all files as resources to the bfabric system.

"""

import os
import sys
sys.path.insert(0, '/export/bfabric/bfabric/.python')
import bfabric
import datetime


if __name__ == "__main__":
    bfapp = bfabric.Bfabric(login='pfeeder')
    bfapp.set_bfabric_webbase("http://fgcz-bfabric.uzh.ch/bfabric")

    RDataObj = {'name': 'RData', 
        'projectid': '1000', 
        'applicationid': 209, 
        'status': 'pending'}

    # create a WU
    workunit = bfapp.save_object(endpoint='workunit', obj=RDataObj)[0]

    # add files as resources to the workunit._id

    for i in [1, 2]:
        ResourceObj = {
            'size' : 0,
            'storageid' : 2,
            'description' : 'bla bla',
            'relativepath' : '/p1000/test',
            'status' : 'available',
            'workunitid' : workunit._id}

        resource = bfapp.save_object(endpoint='resource', obj=ResourceObj)
        print resource

    WorkunitObj = {'id': workunit._id, 
        'status': 'available'}

    workunit = bfapp.save_object(endpoint='workunit', obj=WorkunitObj)
    print workunit



    #print (workunit)
    #map(lambda x: sys.stdout.write("{0}\t{1}\t{2}\n".format(x._id, x.createdby, x.modified)), workunit)
    #sys.exit(0)

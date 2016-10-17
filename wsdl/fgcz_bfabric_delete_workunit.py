#!/usr/bin/python
# -*- coding: latin1 -*-

"""
Copyright (C) 2016 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
  Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn/repos/scripts/trunk/linux/bfabric/apps/python/fgcz_bfabric_delete_workunit.py $
$Id: fgcz_bfabric_delete_workunit.py 2397 2016-09-06 07:04:35Z cpanse $ 

"""



import sys
#sys.path.insert(0, '/export/bfabric/bfabric/.python')
import bfabric

def delete_workunit(workunitid):
    res = bfapp.delete_object(endpoint='workunit', id=workunitid)
    print res


if __name__ == "__main__":
    bfapp = bfabric.Bfabric(login='pfeeder')
    bfapp.set_bfabric_webbase("http://fgcz-bfabric.uzh.ch/bfabric")

    if len(sys.argv) > 1:
        for i in range(1, len(sys.argv)):
            delete_workunit(workunitid=sys.argv[i])


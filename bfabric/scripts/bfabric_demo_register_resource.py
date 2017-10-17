#!/usr/bin/python
# -*- coding: latin1 -*-

# $Id: bfabric_demo_register_resource.py 2906 2017-06-12 10:55:55Z cpanse $
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_demo_register_resource.py $
# $Date: 2017-06-12 12:55:55 +0200 (Mon, 12 Jun 2017) $



import os
import re
import time
import sys
import bfabric


def main():
    BFABRICSTORAGEID = 2
    bfapp = bfabric.BfabricFeeder()

    # create workunit
    wuobj = { 'applicationid': 155,
            'projectid': 2135,
            'name': 'mascot2RData',
            }
    #res = bfapp.save_object(endpoint='workunit', obj=wuobj)
    #print res
    #sys.exit(1)
    # add resource 155566

    resobj = { 'workunitid': 155568,
            'filechecksum': '001060d57a9755dfe19affd3c3882caf',
            'status': 'available',
            #'filedate': time.strftime("%FT%H:%M:%S-01:00", time.gmtime()),
            'relativepath': '/p2135/bfabric/Proteomics/mascot2RData/2017/2017-06/2017-06-12/20170612.RData',
            'name': 'mascot2RData',
            'size': 11254202,
            'storageid': 2
            }

    res = bfapp.save_object(endpoint='resource', obj=resobj)
    print res

    # make it available
    wuobj = { 'id': 155568,
            'status': 'available'}

    res = bfapp.save_object(endpoint='workunit', obj=wuobj)
    print res


if __name__ == "__main__":
    main()


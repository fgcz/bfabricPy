#!/usr/bin/env python
# -*- coding: latin1 -*-

"""

Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_list_proteomics_projects.py $
$Id: bfabric_list_proteomics_projects.py 2540 2016-10-25 11:55:35Z cpanse $ 



http://fgcz-bfabric.uzh.ch/bfabric/executable?wsdl

"""

import sys
from bfabric import Bfabric

#def size_extract(
bfapp = Bfabric()

def bfabric_stat(id):

    ne = 0
    ns = 0
    nw = 0
    ni = 0
    nr = 0

    try:
        res_extract = bfapp.read_object(endpoint='extract', obj={'projectid':id})
        ne = len(res_extract)
    except:
        pass

    try:
        res_sample = bfapp.read_object(endpoint='sample', obj={'projectid':id})
        ns = len(res_sample)
    except:
        pass

    try:
        res_workunit = bfapp.read_object(endpoint='workunit', obj={'projectid':id})
        nw = len(res_workunit)
    except:
        pass

    try:
        res_importresource = bfapp.read_object(endpoint='importresource', obj={'projectid':id})
        ni = len(res_importresource)
    except:
        pass

    try:
        res_resource = bfapp.read_object(endpoint='resource', obj={'projectid':id})
        nr = len(res_resource)
    except:
        pass

    return [id, ns, ne, nw, ni, nr]

if __name__ == "__main__":


    print "project.id,nsamples,nextracts,nworkunits,nimportresource,nresource,coach.login,servicemode"
    #for pid in reversed(range(1500, 2310)):
    for pid in reversed(range(1500, 1510)):
        try:
            res_project = bfapp.read_object(endpoint='project', obj={'id':pid})[0]
            # print res_project
            # sys.exit(0)
            if 'Proteomics' in res_project.technology:
                coach = bfapp.read_object(endpoint='user', obj={'id':res_project.coach[0]})[0]
                res = bfabric_stat(pid) 
                print "{},{},{},{},{},{},{},{}".format(res[0], res[1], res[2], res[3], res[4], res[5], coach.login, res_project.servicemode)
        except:
            pass

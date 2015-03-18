#!/usr/bin/python
# -*- coding: latin1 -*-

"""
just a test script
"""

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmid <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/test.py $
# $Id: test.py 1289 2014-01-31 06:49:24Z cpanse $

import os
import sys
import base64
import bfabric


if __name__ == "__main__":

    # bfapp = bfabric.BfabricExternalJob(login='pfeeder', externaljobid=13668)

    bfapp = bfabric.BfabricSubmitter(login='pfeeder', externaljobid=13909)
    print bfapp.get_executable_of_externaljobid()
    sys.exit(0)


    print bfapp.save_object('executable', { 'id':4521, 'name':'test' , 'base64': base64.b64encode("# This is just another bash script!")})

    print bfapp.read_object('wrappercreator', { 'id': 6} )

    #print bfapp.read_object('externaljob', { 'executableid': 4514} )[0]._id
    print bfapp.read_object('externaljob', { 'cliententityid': 112281} )
    print bfapp.read_object('executable', { 'id': 4503} )
    # print bfapp.read_object('workunit', { 'id': 112275} )
    # print bfapp.read_object('executable', { 'id':4500 } )

    externaljobid=13829
    res = bfapp.save_object(endpoint='externaljob', obj={'id':externaljobid, 'status':'done'})
    print res
    # print bfapp.save_object(endpoint='externaljob', obj={'id':13829, 'status':'done'})
    sys.exit(1)
    print bfapp.read_object('storage', { 'id': 2} )
    print bfapp.read_object('application', { 'id': 152} )
    print bfapp.read_object('resource', { 'id': 144112} )


    res0 = bfapp.read_object('application', { 'id': 152 } )[0]
    print res0
    print str(res0.technology).replace(' ', '_')
    print res0.name
#    print res0.tecnology

    res0 = bfapp.save_object('resource', { 
        'name': 'test', 
        'workunitid':112242,
        'weburl':'www.google.de',
        'storageid':2,
        'relativepath':'/srv/www/htdocs/p403/bfabric/Proteomics/testing/'})[0]

    filename = res0.relativepath + str(res0._id)
    res1 = bfapp.save_object('resource', { 
        'id': res0._id, 
        'relativepath': res0.relativepath + str(res0._id)})

    with open(filename, 'w') as f:
        f.write(repr(res1))
   
    print bfapp.report_resource(res0._id)

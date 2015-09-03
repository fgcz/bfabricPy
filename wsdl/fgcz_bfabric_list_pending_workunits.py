#!/usr/bin/python
# -*- coding: latin1 -*-

"""
A wrapper_creator for B-Fabric
Gets an external job id from B-Fabric
Creates an executable for the submitter

after successfull uploading the executables the wrapper creator creates an
externaljob
"""

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn/repos/scripts/trunk/linux/bfabric/apps/python/wrapper_creator.py $
# $Id: wrapper_creator.py 1289 2014-01-31 06:49:24Z cpanse $ 

import os
import sys
sys.path.insert(0, '/export/bfabric/bfabric/.python')
import bfabric
import datetime

if __name__ == "__main__":
    bfapp = bfabric.Bfabric(login='pfeeder')
    bfapp.set_bfabric_webbase("http://fgcz-bfabric.uzh.ch/bfabric")


    workunitid=133034
    workunitid=133702

    workunit = bfapp.read_object(endpoint='workunit', obj={'status': 'pending'})
    map(lambda x: sys.stdout.write("{0}\t{1}\t{2}\n".format(x._id, x.createdby, x.modified)), workunit)
    sys.exit(0)

    workunit = workunit[0]

    resource = map(lambda x: x._id, workunit.inputresource)
    resource = map(lambda x: bfapp.read_object(endpoint='resource', obj={'id': x})[0], resource)
    print resource
    inputFile = map(lambda x: x.relativepath, resource)
    inputStorageObj = map(lambda x: bfapp.read_object('storage', {'id': x.storage._id}) , resource)
    inputHostBasePath=map(lambda x: "{0}:{1}".format(x[0].host, x[0].basepath), inputStorageObj)
    inputFile = " ".join(["%s/%s" % t for t in zip(inputHostBasePath, inputFile)])
    print inputFile
    extractId = map(lambda x: x.extract._id, resource)
    sampleId = map(lambda x: bfapp.read_object(endpoint='extract', obj={'id': x})[0].sample._id, extractId)
    customattribute = map(lambda x: bfapp.read_object(endpoint='sample', obj={'id':x})[0].customattribute, sampleId)
    customValues=map(lambda x: map(lambda xx: xx.value, x), customattribute)

    print customValues





    #extractid=31013
    #extract = bfapp.read_object(endpoint='extract', obj={'id': extractid})
    #print extract

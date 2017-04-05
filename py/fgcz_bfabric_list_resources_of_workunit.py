#!/usr/bin/python
# -*- coding: latin1 -*-

"""

Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
  Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/fgcz_bfabric_list_resources_of_workunit.py $
$Id: fgcz_bfabric_list_resources_of_workunit.py 2397 2016-09-06 07:04:35Z cpanse $ 

"""



#sys.path.insert(0, '/export/bfabric/bfabric/.python')
import bfabric

def get_extract(workunitid):
    workunit = bfapp.read_object(endpoint='workunit', obj={'id': workunitid})[0]

    resources = map(lambda x: bfapp.read_object('resource', obj={'id':x._id})[0], workunit.inputresource)

    for i in resources:
        print "resourceid={0}".format(i._id)
        try:
            print "extractid={0}".format(i.extract._id)
            extract = bfapp.read_object('extract', obj={'id': i.extract._id})[0]
            try:
                print "sampleid={0}".format(extract.sample._id)
            except:
                pass
            #print extract
        except:
            try:
                get_extract(i.workunit._id)
            except:
                print "ERROR"



if __name__ == "__main__":
    bfapp = bfabric.Bfabric(login='pfeeder')
    bfapp.set_bfabric_webbase("http://fgcz-bfabric.uzh.ch/bfabric")

    workunitid=134939


    get_extract(workunitid)


    #print map(lambda x: bfapp.read_object(endpoint='extract', obj={'id': x.extractid}), workunit.inputresource)

    #resources = bfapp.read_object(endpoint='resource', obj={'workunitid': workunitid})

    #print resources[0]
    #print map(lambda x: bfapp.read_object(endpoint='extract', obj={'id': x.extractid}), resources)

    #map(lambda x: sys.stdout.write("{0}\t{1}\t{2}\n".format(x._id, x.createdby, x.modified)), workunit)


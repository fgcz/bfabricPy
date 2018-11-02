#!/usr/bin/python

"""
Christian Panse <cp@fgcz.ethz.ch>
2018-09-03 FGCZ
"""

import sys
import os
import yaml
import xmlrpclib
import hashlib
from optparse import OptionParser
from bfabric import Bfabric

HTTPROOT=""
BFABRICSTORAGEID = 2

"""
 links an resource to an existing import resources in bfabric.
 
 example
 bfabric_save_resource.py p1000 244 p1000/Proteomics/QEXACTIVEHFX_1/paolo_20180903_autoQC/mgf_rawDiag/20180903_02_autoQC02.mgf
"""
def save_resource(projectid=None, resource_file=None, applicationid=None):
    if projectid is None or resource_file is None or applicationid is None:
        print "at least one of the arguments is None."
        sys.exit(1)

    # assert type(projectid) is 'int'
    resource_file = resource_file.replace("/src/www/htdocs", "/")
    bfapp = Bfabric()

    try:
        print "reading stdin"
        description = sys.stdin.read()
    except:
        print "reading from stdin failed."
        raise

    try:
        md5 = hashlib.md5(open(resource_file, 'rb').read()).hexdigest()
    except:
        print "computing file checksum failed."
        raise

    resource = bfapp.read_object(endpoint='resource', obj={'filechecksum': md5})

    try:    
        print "resource(s) already exist.".format(resource[0]._id)
        resource = bfapp.save_object(endpoint='resource', obj={'id': resource[0]._id, 'description': description,
                                                               'relativepath': "{}{}".format(HTTPROOT, resource_file),})
        print resource
        return
    except:
        pass


    try:
        workunit = bfapp.save_object(endpoint='workunit',
                                 obj={'name': "MGF: {}".format(resource_file),
                                      'projectid': projectid,
                                      'applicationid': applicationid})
        print (workunit)
    except:
        raise


    obj = {'workunitid': workunit[0]._id,
           'filechecksum': md5,
           'relativepath': "{}{}".format(HTTPROOT, resource_file),
           'name': os.path.basename(resource_file),
           'size': os.path.getsize(resource_file),
           'status': 'available',
           'description': description,
           'storageid': BFABRICSTORAGEID
           }


    resource = bfapp.save_object(endpoint='resource', obj=obj)
    print resource

    workunit = bfapp.save_object(endpoint='workunit',
                                 obj={'id': workunit[0]._id, 'status': 'available'})
    print (workunit)

if __name__ == "__main__":
    assert len(sys.argv) == 4

    #save_resource(projectid=1000)
    save_resource(projectid=sys.argv[1], resource_file=sys.argv[3], applicationid=sys.argv[2])
    # TODO(cp):
    #              importresourcefilechecksum=sys.argv[4])

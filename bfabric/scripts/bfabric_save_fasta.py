#!/usr/bin/python

import sys
import os
import yaml
#import xmlrpclib
import hashlib
from optparse import OptionParser
from bfabric import Bfabric

FASTAHTTPROOT="/fasta/"
BFABRICSTORAGEID = 2
BFABRICAPPLIATIONID = 61

def save_fasta(containerid=1875, fasta_file="p1875_db10_20170817.fasta"):
    bfapp = Bfabric()

    try:
        print("reading stdin")
        description = sys.stdin.read()
    except:
        print("reading from stdin failed.")
        raise

    try:
        md5 = hashlib.md5(open(fasta_file, 'rb').read()).hexdigest()
    except:
        print("computing file checksum failed.")
        raise

    resource = bfapp.read_object(endpoint='resource', obj={'filechecksum': md5})

    try:    
        print("resource(s) already exist.".format(resource[0]._id))
        resource = bfapp.save_object(endpoint='resource', obj={'id': resource[0]._id, 'description': description})
        print(resource)
        return
    except:
        pass


    try:
        workunit = bfapp.save_object(endpoint='workunit',
                                 obj={'name': "FASTA: {}".format(os.path.basename(fasta_file)),
                                      'containerid': containerid,
                                      'applicationid': BFABRICAPPLIATIONID})
        print (workunit)
    except:
        raise


    obj = {'workunitid': workunit[0]._id,
           'filechecksum': md5,
           'relativepath': "{}{}".format(FASTAHTTPROOT, os.path.basename(fasta_file)),
           'name': os.path.basename(fasta_file),
           'size': os.path.getsize(fasta_file),
           'status': 'available',
           'description': description,
           'storageid': BFABRICSTORAGEID
           }


    resource = bfapp.save_object(endpoint='resource', obj=obj)
    print(resource)

    workunit = bfapp.save_object(endpoint='workunit',
                                 obj={'id': workunit[0]._id, 'status': 'available'})
    print (workunit)

if __name__ == "__main__":
    save_fasta(containerid=sys.argv[1], fasta_file=sys.argv[2])


    #p#rint (workunit)

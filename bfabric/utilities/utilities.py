import os
import hashlib

from bfabric.bfabric import Bfabric

def save_fasta(projectid=1875,
               fasta_file="p1875_db10_20170817.fasta",
               description_resource="",
               description_workunit="",
               fasta_http_root="/fasta/",
               bfabric_storage_id=2,
               bfabric_application_id=61):


    bfapp = Bfabric()
    try:
        md5 = hashlib.md5(open(fasta_file, 'rb').read()).hexdigest()
    except:
        print("computing file checksum failed.")
        raise

    resource = bfapp.read_object(endpoint='resource', obj={'filechecksum': md5})

    if resource is not None:
        print("resource(s) {} already exist.".format(resource[0]._id))
        resource = bfapp.save_object(endpoint='resource', obj={'id': resource[0]._id, 'description': description_resource})
        print(resource)
        return

    data_fasta = {'name': "FASTA: {}".format(os.path.basename(fasta_file)),
     'projectid': projectid,
     'applicationid': bfabric_application_id,
     'description': description_workunit}
    try:
        workunit = bfapp.save_object(endpoint='workunit',
                                 obj=data_fasta)
        print(workunit)
    except:
        raise


    obj = {'workunitid': workunit[0]._id,
           'filechecksum': md5,
           'relativepath': "{}{}".format(fasta_http_root, os.path.basename(fasta_file)),
           'name': os.path.basename(fasta_file),
           'size': os.path.getsize(fasta_file),
           'status': 'available',
           'description': description_resource,
           'storageid': bfabric_storage_id
           }


    resource = bfapp.save_object(endpoint='resource', obj=obj)
    print(resource)

    workunit = bfapp.save_object(endpoint='workunit',
                                 obj={'id': workunit[0]._id,
                                      'status': 'available'})
    return(workunit)

#!/usr/bin/python


import sys
import base64
from bfabric import Bfabric


if __name__ == "__main__":
    bfapp = Bfabric()


    resource_filename = "bfabric_upload_resource.py"
    project_id = 1000
    application_id = 211


    with open(resource_filename, 'r') as f:
        resource_content = f.read()

    try:
        resource_base64 = base64.b64encode(resource_content)
    except:
        raise



    res = bfapp.save_object(endpoint='workunit', obj={'name':'211 upload resource', 'projectid':1000, 'applicationid':211})
    print res

    workunit_id = res[0]._id
    res = bfapp.save_object('resource', {'base64': resource_base64, 'name': resource_filename, 'workunitid':workunit_id})
    print res

    res = bfapp.save_object('workunit', {'id': workunit_id, 'status': 'available'})
    print res

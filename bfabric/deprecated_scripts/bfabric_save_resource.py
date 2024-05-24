#!/usr/bin/env python3


"""
author:
    Christian Panse <cp@fgcz.ethz.ch>
    20200424-1300

input:

description:
    registers a resource in bfabric



usage:

# on the bash
resourcefile=/srv/www/htdocs/p3061/Proteomics/Analysis/fragpipe/cpanse_20200424/DS32024.zip

[ $? -eq 0 ] \
  && unzip -l ${resourcefile} \
  | ./bfabric_save_resource.py -p 3000 -a 273 -r ${resourcefile} --stdin

"""


import sys
import os
import yaml
import hashlib
from optparse import OptionParser
from bfabric import Bfabric
import getopt

assert sys.version_info >= (3, 6)

BFABRICSTORAGEID = 2


def save_resource(projectid=None, resourcefile=None, applicationid=None, read_stdin=False):

    bfapp = Bfabric()
    description = None

    print("DEBUG {}".format(read_stdin))
    if read_stdin is True:
        try:
            print("reading stdin")
            description = sys.stdin.read()
        except:
            print("reading from stdin failed.")
            raise

    try:
        md5 = hashlib.md5(open(resourcefile, "rb").read()).hexdigest()
    except:
        print("computing file checksum failed.")
        raise

    resource = bfapp.read_object(endpoint="resource", obj={"filechecksum": md5})

    try:
        print("resource(s) already exist.".format(resource[0]._id))
        resource = bfapp.save_object(endpoint="resource", obj={"id": resource[0]._id, "description": description})
        print(resource[0])
        return
    except:
        pass

    try:
        workunit = bfapp.save_object(
            endpoint="workunit",
            obj={
                "name": "{}".format(os.path.basename(resourcefile)),
                "projectid": projectid,
                "applicationid": applicationid,
            },
        )
        print(workunit)
    except:
        raise

    obj = {
        "workunitid": workunit[0]._id,
        "filechecksum": md5,
        "relativepath": "{}".format(resourcefile),
        "name": os.path.basename(resourcefile),
        "size": os.path.getsize(resourcefile),
        "status": "available",
        "description": description,
        "storageid": BFABRICSTORAGEID,
    }

    resource = bfapp.save_object(endpoint="resource", obj=obj)[0]
    print(resource)

    workunit = bfapp.save_object(endpoint="workunit", obj={"id": workunit[0]._id, "status": "available"})
    print(workunit)


if __name__ == "__main__":
    # resource_file = "/srv/www/htdocs/p3061/Proteomics/Analysis/fragpipe/cpanse_20200424/DS32024.zip"
    # save_resource(projectid=3061, resource_file=resource_file, applicationid=274)

    (projectid, applicationid, resourefile) = (None, None, None)
    read_stdin = False

    try:
        opts, args = getopt.getopt(
            sys.argv[1:], "hp:a:r:", ["help", "projectid=", "applicationid=", "resourcefile=", "stdin"]
        )
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit(0)
        if o in ("-", "--stdin"):
            read_stdin = True
        elif o in ("-p", "--projectid"):
            projectid = a
        elif o in ("-a", "--applicationid"):
            applicationid = a
        elif o in ("-r", "--resourcefile"):
            resourcefile = a
            try:
                os.path.isfile(resourcefile)
            except:
                print("can not access file '{}'".format(resourcefile))
                raise
        else:
            usage()
            assert False, "unhandled option"

    if projectid is None or resourcefile is None or applicationid is None:
        msg = "at least one of the arguments is None."
        sys.stderr.write("\033[93m{}\033[0m\n".format(msg))
        sys.stdout.write(__doc__)
        sys.exit(1)
    save_resource(projectid, resourcefile, applicationid, read_stdin)

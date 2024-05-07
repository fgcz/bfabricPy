#!/usr/bin/python

import sys
import os
import yaml
import xmlrpclib
from optparse import OptionParser

if __name__ == "__main__":
    print "this code is under construction."
    print "bfabric_save.py executable id valid=false"
    sys.exit(1)

    parser = OptionParser(usage="usage: %prog -h <hostname>",
                          version="%prog 1.0")


    parser.add_option("-c", "--config",
                      type='string',
                      action="store",
                      dest="config_filename",
                      default=None,
                      help="provide a yaml formated config file")

    parser.add_option("-q", "--query",
                      type='string',
                      action="store",
                      dest="query",
                      default="all",
                      help="provide: output|workunit|wu")


    (options, args) = parser.parse_args()

    if options.config_filename is None:
        print "ERROR: provide a config filename."
        sys.exit(1)

    try:
        with open(options.config_filename, 'r') as f:
            content = f.read()
            
        job_config = yaml.load(content)

    except:
        print "ERROR: parsing file '{0}' failed.".format(options.config_filename)
        raise


    if options.query == "output":
        print job_config['application']['output'][0]
    elif options.query == "wu":
        print "wu{0}".format(job_config['job_configuration']['workunit_id'])
    elif options.query == "external_job_id":
        print "{0}".format(job_config['job_configuration']['external_job_id'])
    elif options.query == "resource_id":
        print "{0} {1} {2}".format(job_config['job_configuration']['output']['resource_id'], job_config['job_configuration']['stderr']['resource_id'], job_config['job_configuration']['stdout']['resource_id'])
    else:
        print job_config

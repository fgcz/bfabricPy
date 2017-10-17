#!/usr/bin/python


import sys
import os
import yaml
import xmlrpclib
from optparse import OptionParser



if __name__ == "__main__":

    parser = OptionParser(usage="usage: %prog -h <hostname>",
                          version="%prog 1.0")


    parser.add_option("-c", "--config",
                      type='string',
                      action="store",
                      dest="config_filename",
                      default=None,
                      help="provide a yaml formated config file")

    parser.add_option("-n", "--hostname",
                      type='string',
                      action="store",
                      dest="hostname",
                      default="localhost",
                      help="provide a hostname")

    parser.add_option("-p", "--port",
                      type='int',
                      action="store",
                      dest="port",
                      default="8085",
                      help="provide a port number")

    parser.add_option("-o", "--outputurl",
                      type='string',
                      action="store",
                      dest="outputurl",
                      default="bfabric@fgcz-s-021.uzh.ch:/scratch/dump.zip",
                      help="provide a output url")



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


    try:
        print "try to connect to host {} port {}".format(options.hostname, options.port)
        pd_wrapper = xmlrpclib.ServerProxy("http://{0}:{1}/".format(options.hostname, options.port))
    except:
        print "ERROR: failed starting rpc proxy client"
        raise

    pd_wrapper.add_config(job_config)
    pd_wrapper.add_outputurl(options.outputurl)

    rv = pd_wrapper.print_config()

    try:
        rv = pd_wrapper.run()
        print rv
    except:
        print "return code is not 0"
        pass

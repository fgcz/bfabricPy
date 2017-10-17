#!/usr/bin/python


import sys
import os

from SimpleXMLRPCServer import SimpleXMLRPCServer

from fgcz_pd_wrapper import FgczPDWrapper
from optparse import OptionParser

if __name__ == "__main__":
    """

    """

    parser = OptionParser(usage="usage: %prog -h <hostname>",
                          version="%prog 1.0")

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
                      help="provide a hostname")



    (options, args) = parser.parse_args()


    pdw = FgczPDWrapper()

    print "run server on port={}".format(options.port)
    server = SimpleXMLRPCServer((options.hostname, options.port))

    server.register_instance(pdw)

    server.serve_forever()

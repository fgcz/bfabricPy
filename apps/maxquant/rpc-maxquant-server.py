#!/usr/bin/python
# -*- coding: latin1 -*-


import os
import urllib
import signal
import platform
import socket
import subprocess
import shlex
import time
import datetime
import getopt
import sys
import re
import xml.dom.minidom
import multiprocessing
import logging
import logging.handlers
import hashlib


import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer


def maxquant(config=None):
    return "HELLO FROM RPC SERVER")


if __name__ == "__main__":
    #print crawl()
    port = 9999
    server = SimpleXMLRPCServer(("130.60.81.74", port))
    print "Listening on port {0} ...".format(port)
    server.register_function(maxquant, "maxquant")
    server.serve_forever()

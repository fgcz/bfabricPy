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

def myExecWorker0(cmdLine):
    myPid = None
    rcode = None

    print "exec|cmd='{0}'".format(cmdLine)
    try:
        tStart = time.time()
        p = subprocess.Popen(cmdLine, shell=True)

        myPid = p.pid
        rcode = p.wait()

        tStop = time.time()

        p.terminate()

    except OSError as e:
        print "exception|pid={0}|OSError={1}".format(myPid, e)

    print "completed|pid={0}|time={1}|cmd='{2}'".format(myPid, tStop - tStart, cmdLine)

    return rcode


def maxquant(config=None):
    return "HELLO FROM RPC SERVER")


if __name__ == "__main__":
    #print crawl()
    port = 9999
    server = SimpleXMLRPCServer(("130.60.81.74", port))
    print "Listening on port {0} ...".format(port)
    server.register_function(myExecWorker0(, "worker")
    server.serve_forever()

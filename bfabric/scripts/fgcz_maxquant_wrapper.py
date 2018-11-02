#!/usr/bin/python3
# -*- coding: latin1 -*-

# Copyright (C) 2017 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/fgcz_pd_wrapper.py $
# $Id: fgcz_pd_wrapper.py 2992 2017-08-17 13:37:36Z cpanse $

import logging
import logging.handlers
import os
import pprint
import re
# mport shutil
# import subprocess
import sys
import time
import urllib
# from os import listdir

from optparse import OptionParser
from typing import TextIO

from lxml import etree

import yaml

# from bfabric import Bfabric

import hashlib

"""
requirements
- file system mounted via NFS

"""


class FgczMaxQuantConfig:
    """

  input:
    QEXACTIVE_2:
    - bfabric@fgczdata.fgcz-net.unizh.ch://srv/www/htdocs//p1946/Proteomics/QEXACTIVE_2/paolo_20150811_course/20150811_01_Fetuin40fmol.raw
    - bfabric@fgczdata.fgcz-net.unizh.ch://srv/www/htdocs//p1946/Proteomics/QEXACTIVE_2/paolo_20150811_course/20150811_02_YPG1.raw
  output:

    """

    config = None
    scratchdir = None

    def __init__(self, config=None):

        #self.bf = Bfabric()
        #if not os.path.isdir(self.scratchroot):
        #    try:
        #        os.mkdir(self.scratchroot)
        #    except:
        #        print "scratch '{0}' does not exists.".format(self.scratchroot)
        #        raise
        if config:
            self.config = config
            self.scratchdir = "/scratch/MAXQUANT/WU{}".format(self.config['job_configuration']['workunit_id'])
            print (self.scratchdir)
            if not os.path.isdir(self.scratchdir):
                raise SystemError



    def generate_mqpar(self, xml_filename):
        with open("/home/bfabric/sgeworker/bin/mqpar_v1623_j.xml", 'r') as f:
            mqpartree = etree.parse(f)


        
        """ PARAMETER """
        for query, value in self.config['application']['parameters'].items():
            element = mqpartree.find(query)
            if element is not None:
                if value == "None":
                    element.text = ''
                elif query == "/parameterGroups/parameterGroup/variableModifications":
                    for a in value.split(","):
                      estring = etree.Element("string")
                      estring.text = a
                      element.append(estring)
                    pass
                else:
                    print ("replacing xpath expression {} by {}.".format(query, value))
                    element.text = value

        ecount = 0;
        """ INPUT """
        for query, value in self.config['application']['input'].items():
            for input in self.config['application']['input'][query]:
                element = mqpartree.find("/filePaths")
                if element is None:
                    raise TypeError


                host, file = input.split(":")

                print ("{}\t{}".format(os.path.basename(input), file))

                if not os.path.isfile(file):
                    raise SystemError

                targetRawFile = "{}/{}".format(self.scratchdir, os.path.basename(input))

                if not os.path.islink(targetRawFile):
                     os.symlink(file,  targetRawFile)

                estring = etree.Element("string")
                estring.text = targetRawFile
                element.append(estring)

                element = mqpartree.find("/experiments")
                if element is None:
                    raise TypeError

                estring = etree.Element("string")
                estring.text = "{}".format(os.path.basename(input).replace(".raw", "").replace(".RAW", ""))
                ecount += 1
                element.append(estring)

                element = mqpartree.find("/fractions")
                if element is None:
                    raise TypeError

                estring = etree.Element("short")
                estring.text = "32767"
                element.append(estring)

                element = mqpartree.find("/ptms")
                if element is None:
                    raise TypeError

                estring = etree.Element("boolean")
                estring.text = "false"
                element.append(estring)

                element = mqpartree.find("/paramGroupIndices")
                if element is None:
                    raise TypeError

                estring = etree.Element("int")
                estring.text = "0"
                element.append(estring)

        mqpartree.write(xml_filename)#, pretty_print=True)


    def run(self):
      pass


if __name__ == "__main__":
    parser = OptionParser(usage="usage: %prog -y <yaml formated config file>",
                          version="%prog 1.0")

    parser.add_option("-y", "--yaml",
                      type='string',
                      action="store",
                      dest="yaml_filename",
                      default=None,
                      help="config file.yaml")

    parser.add_option("-x", "--xml",
                      type='string',
                      action="store",
                      dest="xml_filename",
                      default=None,
                      help="maxquant mqpar xml parameter filename.")

    (options, args) = parser.parse_args()

    if not os.path.isfile(options.yaml_filename):
        print ("ERROR: no such file '{0}'".format(options.yaml_filename))
        sys.exit(1)
    try:
        with open(options.yaml_filename, 'r') as f:
            content = f.read()
        job_config = yaml.load(content)
        MQC = FgczMaxQuantConfig(config = job_config)
        MQC.generate_mqpar(options.xml_filename)

    except:
        print ("ERROR: exit 1")
        raise

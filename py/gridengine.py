#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces to the Sun/Oracle/Open Grid Engine batch queueing systems.
taken from https://vm-mad.googlecode.com/svn/trunk
"""
# Copyright (C) 2011, 2012 ETH Zurich and University of Zurich. All rights reserved.
# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Christian Panse <cp@fgcz.ethz.ch>
#   Riccardo Murri <riccardo.murri@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# $Rev: 1269 $
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/gridengine.py $
# $Date: 2016-09-06 09:04:35 +0200 (Tue, 06 Sep 2016) $
# $Author: cpanse $

__docformat__ = 'reStructuredText'
__version__ = '$Revision: 1269 $'

import os
import subprocess

class GridEngine(object):
    """
    interface to Open Grid Sceduler qsub 
    """

    def __init__(self, user='*', queue="PRX@fgcz-c-071", GRIDENGINEROOT='/opt/sge'):
        """
        Set up parameters for querying Grid Engine.

        SGEROOT is essential.
        """

        self.user = user
        self.queue = queue
        self.qsub = "{0}/{1}".format(GRIDENGINEROOT, "bin/lx-amd64/qsub")

        os.environ["SGE_ROOT"] = GRIDENGINEROOT

    def qsub(self, script, arguments=""):
        """
            if qsub and script are files do 
            qsub as fire and forget

            todo: pass stderr and stdout file location as argument
        """
        qsub_cmd = [self.qsub, "-q", self.queue, script, " ".join(arguments)]

        if not os.path.isfile(self.qsub):
            print "{0} can not be found.".format(self.qsub)
            return

        if not os.path.isfile(script):
            print "'{0}' - no such file.".format(script)
            return

        try:
            qsub_process = subprocess.Popen(
                qsub_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False)
            stdout, stderr = qsub_process.communicate()

            return stdout

        except subprocess.CalledProcessError, ex:
            #logging.error("Error running '%s': '%s'; exit code %d", str.join(' ', qstat_cmd), stderr, ex.returncode)
            raise


def main():
    print "hello world!"
    pass

def test():
    print "testing ..."
    pass

if __name__ == "__main__": 
    main()

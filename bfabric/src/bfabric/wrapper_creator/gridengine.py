#! /usr/bin/env python
"""
Interfaces to the Sun/Oracle/Open Grid Engine batch queueing systems.
taken from https://vm-mad.googlecode.com/svn/trunk

https://arxiv.org/abs/1302.2529
DOI: 10.1007/978-3-642-38750-0_34

$Id: gridengine.py 2463 2016-09-23 14:55:50Z cpanse $
$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/gridengine.py $
$Date: 2016-09-23 16:55:50 +0200 (Fri, 23 Sep 2016) $
$Revision: 2463 $
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
# $Rev: 2463 $
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/gridengine.py $
# $Date: 2016-09-23 16:55:50 +0200 (Fri, 23 Sep 2016) $
# $Author: cpanse $

__docformat__ = "reStructuredText"
__version__ = "$Revision: 2463 $"


import os
import subprocess


class GridEngine:
    """
    interface to Open Grid Sceduler qsub
    """

    def __init__(
        self,
        user="*",
        queue="PRX@fgcz-r-035",
        GRIDENGINEROOT="/export/bfabric/bfabric/",
    ):
        """
        Set up parameters for querying Grid Engine.

        SGEROOT is essential.
        """

        self.user = user
        self.queue = queue
        self.qsubbin = f"{GRIDENGINEROOT}/bin/qsub"

        os.environ["SGE_ROOT"] = GRIDENGINEROOT

    def qsub(self, script, arguments=""):
        """
        if qsub and script are files do
        qsub as fire and forget

        todo: pass stderr and stdout file location as argument
        """
        qsub_cmd = [self.qsubbin, "-q", self.queue, script, " ".join(arguments)]

        if not os.path.isfile(self.qsubbin):
            print(f"{self.qsubbin} can not be found.")
            return

        if not os.path.isfile(script):
            print(f"'{script}' - no such file.")
            return

        try:
            qsub_process = subprocess.Popen(qsub_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
            stdout, stderr = qsub_process.communicate()

            return stdout

        # except subprocess.CalledProcessError, ex:
        except:
            # logging.error("Error running '%s': '%s'; exit code %d", str.join(' ', qstat_cmd), stderr, ex.returncode)
            raise


def main():
    print("hello world!")
    pass


if __name__ == "__main__":
    main()

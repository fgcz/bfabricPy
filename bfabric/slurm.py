#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interface to the SLURM (Simple Linux Utility for Resources Management) resource manager and job scheduler

2020-09-28
Maria d'Errico
Christian Panse

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/slurm.py $
"""

# Copyright (C) 2011, 2012 ETH Zurich and University of Zurich. All rights reserved.
# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Christian Panse <cp@fgcz.ethz.ch>
#   Maria d'Errico <maria.derrico@fgcz.ethz.ch>
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

__docformat__ = 'reStructuredText'
#__version__ = '$Revision: 2463 $'



import os
import subprocess

class SLURM(object):
    """
    interface to Slurm sbatch 
    """

    def __init__(self, user='*', SLURMROOT='/usr/'):
        """
        Set up parameters for querying Slurm.

        SLURMROOT is essential.
        """

        self.user = user
        self.sbatchbin = "{0}/{1}".format(SLURMROOT, "bin/sbatch")

        os.environ["SLURM_ROOT"] = SLURMROOT

    def sbatch(self, script, arguments=""):
        """
            todo: pass stderr and stdout file location as argument
        """
        sbatch_cmd = [self.sbatchbin, script, " ".join(arguments)]

        if not os.path.isfile(self.sbatchbin):
            print ("{0} can not be found.".format(self.sbatchbin))
            return

        if not os.path.isfile(script):
            print ("'{0}' - no such file.".format(script))
            return

        try:
            sbatch_process = subprocess.Popen(
                sbatch_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False)
            stdout, stderr = sbatch_process.communicate()

            return stdout

        # except subprocess.CalledProcessError, ex:
        except:
            raise



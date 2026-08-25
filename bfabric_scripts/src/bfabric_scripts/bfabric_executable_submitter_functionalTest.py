#!/usr/bin/env python3

"""
Submitter for B-Fabric functional test
"""

# Copyright (C) 2014,2015 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
# Modified to submit to the Slurm scheduler on 2020-09-28
#
# Authors:
#   Christian Panse <cp@fgcz.ethz.ch>
#   Maria d'Errico <maria.derrico@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
#
# @name: bfabric_executable_submitter_functionalTest.py
# @description: this script is a dummy submitter executable used by the bfabricPy functional test
# @context: SUBMITTER
# @oarameter: string, q, bfabric,true,true,queue,this is a queue
# @version: $Rev: 1232 $

"""
this is a dummy submitter executable


example:

python bfabric_executable_submitter_functionalTest.py -j 45864
"""


# import os
# import sys
from optparse import OptionParser


def main() -> None:
    parser = OptionParser(usage="usage: %prog -j <externaljobid>", version="%prog 1.0")

    parser.add_option(
        "-j",
        "--externaljobid",
        type="int",
        action="store",
        dest="externaljobid",
        default=None,
        help="external job id is required.",
    )

    (options, args) = parser.parse_args()

    if not options.externaljobid:
        parser.error("option '-j' is required.")

    print("Dummy submitter xecutable defined for the bfabricPy functional test")


if __name__ == "__main__":
    main()

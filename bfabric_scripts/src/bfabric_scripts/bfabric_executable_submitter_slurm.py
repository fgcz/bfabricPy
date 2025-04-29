#!/usr/bin/env python3

"""
Submitter for B-Fabric
"""

from argparse import ArgumentParser

from bfabric import Bfabric
from bfabric.wrapper_creator.bfabric_submitter import BfabricSubmitter

# Copyright (C) 2014,2015 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
# Modified to submit to the Slurm scheduler on 2020-09-28
#
# Authors:
#   Marco Schmid <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#   Maria d'Errico <maria.derrico@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
#
# @name: bfabric_executable_submitter_slurm.py
# @description: this script submits to the Slurm scheduler
# @context: SUBMITTER
# @oarameter: string, q, bfabric,true,true,queue,this is a queue
# @version: $Rev: 1232 $

"""
this is the submitter executable


example:

python bfabric_executable_submitter_slurm.py -j 45864
"""


def main() -> None:
    parser = ArgumentParser(help="Submitter for B-Fabric")
    parser.add_argument("-j", "--externaljobid", type=int)
    args = parser.parse_args()
    client = Bfabric.connect()
    bfapp = BfabricSubmitter(
        client=client,
        externaljobid=args.externaljobid,
        scheduleroot="/usr/",
        scheduler="Slurm",
    )
    bfapp.submitter_yaml()


if __name__ == "__main__":
    main()

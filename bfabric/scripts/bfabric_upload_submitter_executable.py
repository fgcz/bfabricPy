#!/usr/bin/python
# -*- coding: latin1 -*-

"""
Uploader for B-Fabric
"""

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
# Copyright (C) 2020 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Maria d'Errico <maria.derrico@fgcz.ethz.ch>
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Last modified on October 22nd 2020
#
# Licensed under  GPL version 3
#
#
# Usage: bfabric_upload_submitter_executable.py [-h] filename {slurm,gridengine}
#
# Arguments for new submitter executable. For more details run:
# ./bfabric_upload_submitter_executable.py --help
#
# positional arguments:
#   filename            Bash executable of the submitter
#   {slurm,gridengine}  Valid engines for job handling are: slurm, gridengine
#
#


import os
import sys
import base64
from bfabric import Bfabric
import argparse

SVN="$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_upload_submitter_executable.py $"

def setup(argv=sys.argv[1:]):
    argparser = argparse.ArgumentParser(description="Arguments for new submitter executable.\nFor more details run: ./bfabric_upload_submitter_executable.py --help") 
    argparser.add_argument('filename', type=str, help="Bash executable of the submitter")
    argparser.add_argument('engine', type=str, choices=['slurm', 'gridengine'], help="Valid engines for job handling are: slurm, gridengine")
    if len(sys.argv) < 3:
        argparser.print_help(sys.stderr)
        sys.exit(1)
    options = argparser.parse_args()
    return options

def main(options):
    executableFileName = options.filename
    engine = options.engine

    bfapp = Bfabric()

    with open(executableFileName, 'r') as f:
        executable = f.read()

    attr = { 'context': 'SUBMITTER', 
        'parameter': {'modifiable': 'true', 
            'required': 'true', 
            'type':'STRING'}, 
        'masterexecutableid': 11871,
        'status': 'available',
        'enabled': 'true',
        'valid': 'true',
        'base64': base64.b64encode(executable.encode()).decode() }

    if engine == "slurm":
        attr['name'] = 'yaml / Slurm executable'
        attr['parameter']['description'] = 'Which Slurm node in partiton PRX should be used.'
        attr['parameter']['enumeration'] = 'fgcz-r-035'
        attr['parameter']['key'] = 'queue'
        attr['parameter']['label'] = 'queue'
        attr['parameter']['value'] = 'fgcz-r-035'
        attr['version'] = 0.1 
        attr['description'] = 'Stage the yaml config file to application using Slurm.'
    elif engine == "gridengine":
        attr['name'] = 'yaml /  Grid Engine executable'
        attr['parameter']['description'] = 'Which Grid Engine queue should be used.'
        attr['parameter']['enumeration'] = 'PRX@fgcz-r-028'
        attr['parameter']['key'] = 'queue'
        attr['parameter']['label'] = 'queue'
        attr['parameter']['value'] = 'PRX@fgcz-r-028' 
        attr['version'] = 3.00 
        attr['description'] = 'Stage the yaml config file to an application using Grid Engine.' 
                                         
    res = bfapp.save_object('executable', attr)

    bfapp.print_yaml(res)


if __name__ == "__main__":
    options = setup()
    main(options)


#!/usr/bin/env python3
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
# Last modified on November 9th 2020
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
# Example of use:
# 
# For bfabric.__version__ <= 10.21
# bfabric_upload_submitter_executable.py bfabric_executable_submitter_functionalTest.py gridengine --name "Dummy - yaml / Grid Engine executable" --description "Dummy submitter for the bfabric functional test using Grid Engine."
#
# For bfabric.__version__ >= 10.22
# ./bfabric_upload_submitter_executable.py bfabric_executable_submitter_functionalTest.py gridengine --name "Dummy_-_yaml___Grid_Engine_executable" --description "test new submitter's parameters"
# ./bfabric_upload_submitter_executable.py bfabric_executable_submitter_functionalTest.py slurm --name "Dummy_-_yaml___Slurm_executable" --description "test new submitter's parameters"
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
    argparser.add_argument('--name', type=str, help="Name of the submitter", required=False)
    argparser.add_argument('--description', type=str, help="Description about the submitter", required=False)
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
        'parameter': [{'modifiable': 'true', 
            'required': 'true', 
            'type':'STRING'},
            {'modifiable': 'true', 
            'required': 'true', 
            'type':'STRING'}],
        'masterexecutableid': 11871,
        'status': 'available',
        'enabled': 'true',
        'valid': 'true',
        'base64': base64.b64encode(executable.encode()).decode() }

    if engine == "slurm":
        attr['name'] = 'yaml / Slurm executable'
        attr['parameter'][0]['description'] = 'Which Slurm partition in partiton PRX should be used.'
        attr['parameter'][0]['enumeration'] = ['prx','maxquant','scaffold','mascot']
        attr['parameter'][0]['key'] = 'partition'
        attr['parameter'][0]['label'] = 'partition'
        attr['parameter'][0]['value'] = 'prx'
        attr['parameter'][1]['description'] = 'Which Slurm nodelist in partiton PRX should be used.'
        attr['parameter'][1]['enumeration'] = ['fgcz-r-[035,028,033,018]','fgcz-r-035','fgcz-r-033','fgcz-r-028','fgcz-r-018']
        attr['parameter'][1]['key'] = 'nodelist'
        attr['parameter'][1]['label'] = 'nodelist'
        attr['parameter'][1]['value'] = 'fgcz-r-[035,033,028,018]'
        attr['version'] = 1.00 
        attr['description'] = 'Stage the yaml config file to application using Slurm.'
    elif engine == "gridengine":
        attr['name'] = 'yaml /  Grid Engine executable'
        attr['parameter'][0]['description'] = 'Which Grid Engine partition should be used.'
        attr['parameter'][0]['enumeration'] = 'PRX'
        attr['parameter'][0]['key'] = 'partition'
        attr['parameter'][0]['label'] = 'partition'
        attr['parameter'][0]['value'] = 'PRX' 
        attr['parameter'][1]['description'] = 'Which Grid Engine node should be used.'
        attr['parameter'][1]['enumeration'] = ['fgcz-r-033','fgcz-r-028','fgcz-r-018']
        attr['parameter'][1]['key'] = 'nodelist'
        attr['parameter'][1]['label'] = 'nodelist'
        attr['parameter'][1]['value'] = 'fgcz-r-028' 
        attr['version'] = 1.00 
        attr['description'] = 'Stage the yaml config file to an application using Grid Engine.' 

    if options.name:
        attr['name'] = options.name
    else:
        pass
    if options.description:
        attr['description'] = options.description
    else:
        pass

    res = bfapp.save_object('executable', attr)

    bfapp.print_yaml(res)


if __name__ == "__main__":
    options = setup()
    main(options)


#!/usr/bin/env python3
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
# Example of use:
#
# For bfabric.__version__ < 0.10.22
#
# ./bfabric_upload_submitter_executable.py bfabric_executable_submitter_functionalTest.py gridengine --name "Dummy - yaml / Grid Engine executable" --description "Dummy submitter for the bfabric functional test using Grid Engine."
#
#
# For bfabric.__version__ >= 0.10.22
#
# ./bfabric_upload_submitter_executable.py bfabric_executable_submitter_slurm.py slurm
#
# ./bfabric_upload_submitter_executable.py bfabric_executable_submitter_functionalTest.py slurm --name "Yaml_Slurm executable - bfabric functional test" --description "Submitter executable for the bfabric functional test using Slurm"
#
# ./bfabric_upload_submitter_executable.py bfabric_executable_submitter_functionalTest.py slurm --name "Dummy_-_yaml___Slurm_executable" --description "test new submitter's parameters"
#
from __future__ import annotations

import argparse
from pathlib import Path

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client
from bfabric_scripts.cli.external_job.upload_submitter_executable import (
    upload_submitter_executable,
)


@use_client
def main(*, client: Bfabric) -> None:
    """Parses command line arguments and calls `main_upload_submitter_executable`."""
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", type=Path, help="Bash executable of the submitter")
    parser.add_argument(
        "engine",
        type=str,
        choices=["slurm"],
        help="Valid engines for job handling are: slurm, gridengine",
    )
    parser.add_argument("--name", type=str, help="Name of the submitter", required=False)
    parser.add_argument(
        "--description",
        type=str,
        help="Description about the submitter",
        required=False,
    )
    options = parser.parse_args()
    upload_submitter_executable(client=client, **vars(options))


if __name__ == "__main__":
    main()

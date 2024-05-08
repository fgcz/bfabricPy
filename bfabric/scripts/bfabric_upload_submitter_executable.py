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

import argparse
import base64

import yaml

from bfabric.bfabric2 import Bfabric


def main_upload_submitter_executable(options) -> None:
    executableFileName = options.filename
    engine = options.engine

    client = Bfabric.from_config(verbose=True)

    with open(executableFileName) as f:
        executable = f.read()

    attr = {
        "context": "SUBMITTER",
        "parameter": [
            {"modifiable": "true", "required": "true", "type": "STRING"},
            {"modifiable": "true", "required": "true", "type": "STRING"},
            {"modifiable": "true", "required": "true", "type": "STRING"},
        ],
        "masterexecutableid": 11871,
        "status": "available",
        "enabled": "true",
        "valid": "true",
        "base64": base64.b64encode(executable.encode()).decode(),
    }

    if engine == "slurm":
        attr["name"] = "yaml / Slurm executable"
        attr["parameter"][0]["description"] = "Which Slurm partition should be used."
        attr["parameter"][0]["enumeration"] = ["prx", "maxquant", "scaffold", "mascot"]
        attr["parameter"][0]["key"] = "partition"
        attr["parameter"][0]["label"] = "partition"
        attr["parameter"][0]["value"] = "prx"
        attr["parameter"][1]["description"] = "Which Slurm nodelist should be used."
        attr["parameter"][1]["enumeration"] = [
            "fgcz-r-[035,028]",
            "fgcz-r-035",
            "fgcz-r-033",
            "fgcz-r-028",
            "fgcz-r-018",
        ]
        attr["parameter"][1]["key"] = "nodelist"
        attr["parameter"][1]["label"] = "nodelist"
        attr["parameter"][1]["value"] = "fgcz-r-[035,028]"
        attr["parameter"][2]["description"] = "Which Slurm memory should be used."
        attr["parameter"][2]["enumeration"] = ["10G", "50G", "128G", "256G", "512G", "960G"]
        attr["parameter"][2]["key"] = "memory"
        attr["parameter"][2]["label"] = "memory"
        attr["parameter"][2]["value"] = "10G"
        attr["version"] = 1.02
        attr["description"] = "Stage the yaml config file to application using Slurm."
    elif engine == "gridengine":
        attr["name"] = "yaml /  Grid Engine executable"
        attr["parameter"][0]["description"] = "Which Grid Engine partition should be used."
        attr["parameter"][0]["enumeration"] = "PRX"
        attr["parameter"][0]["key"] = "partition"
        attr["parameter"][0]["label"] = "partition"
        attr["parameter"][0]["value"] = "PRX"
        attr["parameter"][1]["description"] = "Which Grid Engine node should be used."
        attr["parameter"][1]["enumeration"] = ["fgcz-r-033", "fgcz-r-028", "fgcz-r-018"]
        attr["parameter"][1]["key"] = "nodelist"
        attr["parameter"][1]["label"] = "nodelist"
        attr["parameter"][1]["value"] = "fgcz-r-028"
        attr["version"] = 1.00
        attr["description"] = "Stage the yaml config file to an application using Grid Engine."

    if options.name:
        attr["name"] = options.name
    if options.description:
        attr["description"] = options.description

    res = client.save("executable", attr)
    print(yaml.dump(res))


def main() -> None:
    """Parses command line arguments and calls `main_upload_submitter_executable`."""
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", type=str, help="Bash executable of the submitter")
    parser.add_argument(
        "engine",
        type=str,
        choices=["slurm", "gridengine"],
        help="Valid engines for job handling are: slurm, gridengine",
    )
    parser.add_argument("--name", type=str, help="Name of the submitter", required=False)
    parser.add_argument("--description", type=str, help="Description about the submitter", required=False)
    options = parser.parse_args()
    main(options)


if __name__ == "__main__":
    main()

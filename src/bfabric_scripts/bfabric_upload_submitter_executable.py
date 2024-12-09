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
import base64
from pathlib import Path

import yaml

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging


def main_upload_submitter_executable(
    client: Bfabric, filename: Path, engine: str, name: str | None, description: str | None
) -> None:
    executable = filename.read_text()

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
    else:
        raise NotImplementedError

    if name:
        attr["name"] = name
    if description:
        attr["description"] = description

    res = client.save("executable", attr)
    print(yaml.dump(res))


def main() -> None:
    """Parses command line arguments and calls `main_upload_submitter_executable`."""
    setup_script_logging()
    client = Bfabric.from_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", type=Path, help="Bash executable of the submitter")
    parser.add_argument(
        "engine",
        type=str,
        choices=["slurm"],
        help="Valid engines for job handling are: slurm, gridengine",
    )
    parser.add_argument("--name", type=str, help="Name of the submitter", required=False)
    parser.add_argument("--description", type=str, help="Description about the submitter", required=False)
    options = parser.parse_args()
    main_upload_submitter_executable(client=client, **vars(options))


if __name__ == "__main__":
    main()

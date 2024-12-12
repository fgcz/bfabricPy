from __future__ import annotations

import base64
from pathlib import Path

import yaml

from bfabric import Bfabric


def slurm_parameters() -> list[dict[str, str]]:
    parameters = [{"modifiable": "true", "required": "true", "type": "STRING"} for _ in range(3)]
    parameters[0]["description"] = "Which Slurm partition should be used."
    parameters[0]["enumeration"] = ["prx", "mascot"]
    parameters[0]["key"] = "partition"
    parameters[0]["label"] = "partition"
    parameters[0]["value"] = "prx"
    parameters[1]["description"] = "Which Slurm nodelist should be used."
    parameters[1]["enumeration"] = ["fgcz-r-024", "fgcz-r-033", "fgcz-c-072", "fgcz-c-073"]
    parameters[1]["key"] = "nodelist"
    parameters[1]["label"] = "nodelist"
    parameters[1]["value"] = "fgcz-r-[035,028]"
    parameters[2]["description"] = "Which Slurm memory should be used."
    parameters[2]["enumeration"] = ["10G", "50G", "128G", "256G", "512G", "960G"]
    parameters[2]["key"] = "memory"
    parameters[2]["label"] = "memory"
    parameters[2]["value"] = "10G"
    return parameters


def upload_submitter_executable_impl(
    client: Bfabric, filename: Path, engine: str, name: str | None, description: str | None
) -> None:
    executable = filename.read_text()

    attr = {
        "context": "SUBMITTER",
        "parameter": [],
        "masterexecutableid": 11871,
        "status": "available",
        "enabled": "true",
        "valid": "true",
        "base64": base64.b64encode(executable.encode()).decode(),
    }

    if engine == "slurm":
        name = name or "yaml / Slurm executable"
        description = description or "Submitter executable for the bfabric functional test using Slurm."
        attr["version"] = "1.03"
        attr["parameter"] = slurm_parameters()
    else:
        raise NotImplementedError

    attr["name"] = name
    attr["description"] = description

    res = client.save("executable", attr)
    print(yaml.dump(res))

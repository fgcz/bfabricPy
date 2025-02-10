import base64
from pathlib import Path
from typing import Literal

import yaml

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client


def slurm_parameters() -> list[dict[str, str]]:
    parameters = [{"modifiable": "true", "required": "true", "type": "STRING"} for _ in range(3)]
    parameters[0]["description"] = "Which Slurm partition should be used."
    parameters[0]["enumeration"] = ["prx", "mascot"]
    parameters[0]["key"] = "partition"
    parameters[0]["label"] = "partition"
    parameters[0]["value"] = "prx"
    parameters[1]["description"] = "Which Slurm nodelist should be used."
    parameters[1]["enumeration"] = [
        "fgcz-r-024",
        "fgcz-r-033",
        "fgcz-c-072",
        "fgcz-c-073",
    ]
    parameters[1]["key"] = "nodelist"
    parameters[1]["label"] = "nodelist"
    parameters[1]["value"] = "fgcz-r-[035,028]"
    parameters[2]["description"] = "Which Slurm memory should be used."
    parameters[2]["enumeration"] = ["10G", "50G", "128G", "256G", "512G", "960G"]
    parameters[2]["key"] = "memory"
    parameters[2]["label"] = "memory"
    parameters[2]["value"] = "10G"
    return parameters


@use_client
def upload_submitter_executable(
    filename: Path,
    *,
    client: Bfabric,
    engine: Literal["slurm"] = "slurm",
    name: str = "yaml / Slurm executable",
    description: str = "Submitter executable for Slurm",
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

import shutil
from pathlib import Path
from typing import Literal

import cyclopts

from bfabric import Bfabric
from bfabric.wrapper_creator.bfabric_submitter import BfabricSubmitter

app = cyclopts.App()


def find_slurm_root() -> str:
    sbatch_path = shutil.which("sbatch")
    if sbatch_path:
        return str(Path(sbatch_path).parents[1])
    else:
        return "/usr/"


@app.command
def submitter(external_job_id: int, scheduler: Literal["Slurm"] = "Slurm") -> None:
    slurm_root = find_slurm_root()
    client = Bfabric.from_config()
    submitter = BfabricSubmitter(
        client=client, externaljobid=external_job_id, scheduleroot=slurm_root, scheduler="Slurm"
    )
    submitter.submitter_yaml()


@app.command
def wrapper_creator():
    pass

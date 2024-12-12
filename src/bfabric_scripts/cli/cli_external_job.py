import shutil
from pathlib import Path
from typing import Literal

import cyclopts
from rich.pretty import pprint

from bfabric import Bfabric
from bfabric.wrapper_creator.bfabric_submitter import BfabricSubmitter
from bfabric.wrapper_creator.bfabric_wrapper_creator import BfabricWrapperCreator

app = cyclopts.App()


def find_slurm_root() -> str:
    sbatch_path = shutil.which("sbatch")
    if sbatch_path:
        return str(Path(sbatch_path).parents[1])
    else:
        return "/usr/"


@app.command
def submitter(external_job_id: int, scheduler: Literal["Slurm"] = "Slurm") -> None:
    if scheduler != "Slurm":
        raise NotImplementedError(f"Unsupported scheduler: {scheduler}")
    slurm_root = find_slurm_root()
    client = Bfabric.from_config()
    submitter = BfabricSubmitter(
        client=client, externaljobid=external_job_id, scheduleroot=slurm_root, scheduler="Slurm"
    )
    submitter.submitter_yaml()


@app.command
def wrapper_creator(external_job_id: int) -> None:
    client = Bfabric.from_config()
    creator = BfabricWrapperCreator(client=client, external_job_id=external_job_id)
    pprint(creator.create())

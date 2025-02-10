import shutil
from pathlib import Path
from typing import Literal

import cyclopts
from rich.pretty import pprint

from bfabric import Bfabric
from bfabric.wrapper_creator.bfabric_submitter import BfabricSubmitter
from bfabric.wrapper_creator.bfabric_wrapper_creator import BfabricWrapperCreator
from bfabric.utils.cli_integration import use_client
from bfabric_scripts.cli.external_job.upload_submitter_executable import (
    upload_submitter_executable,
)
from bfabric_scripts.cli.external_job.upload_wrapper_creator_executable import (
    upload_wrapper_creator_executable,
)

app = cyclopts.App()


def find_slurm_root() -> str:
    sbatch_path = shutil.which("sbatch")
    if sbatch_path:
        return str(Path(sbatch_path).parents[1])
    else:
        return "/usr/"


@app.command
@use_client
def submitter(external_job_id: int, scheduler: Literal["Slurm"] = "Slurm", *, client: Bfabric) -> None:
    if scheduler != "Slurm":
        raise NotImplementedError(f"Unsupported scheduler: {scheduler}")
    slurm_root = find_slurm_root()
    submitter = BfabricSubmitter(
        client=client,
        externaljobid=external_job_id,
        scheduleroot=slurm_root,
        scheduler="Slurm",
    )
    submitter.submitter_yaml()


@app.command
@use_client
def wrapper_creator(external_job_id: int, *, client: Bfabric) -> None:
    creator = BfabricWrapperCreator(client=client, external_job_id=external_job_id)
    pprint(creator.create())


app.command(upload_submitter_executable)
app.command(upload_wrapper_creator_executable)

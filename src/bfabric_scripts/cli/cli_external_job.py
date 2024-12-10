from typing import Literal

import cyclopts

from bfabric import Bfabric
from bfabric.wrapper_creator.bfabric_submitter import BfabricSubmitter

app = cyclopts.App()


@app.command
def submitter(external_job_id: int, scheduler: Literal["Slurm"] = "Slurm") -> None:
    client = Bfabric.from_config()
    submitter = BfabricSubmitter(client=client, externaljobid=external_job_id, scheduleroot="/usr/", scheduler="Slurm")
    submitter.submitter_yaml()


@app.command
def wrapper_creator():
    pass

from __future__ import annotations

import argparse
import io
import json
import shlex
import subprocess
import sys

import polars as pl
from loguru import logger

from bfabric import Bfabric
from bfabric.entities import Workunit


def get_slurm_jobs(partition: str, ssh_host: str | None) -> pl.DataFrame:
    """Returns the active slurm jobs from the specified partition, if it is intended to be run remotely the
    ssh host can be specified.
    """
    target_command = ["squeue", "-p", partition, "--format=%i\t%j\t%N"]
    if ssh_host is None:
        command = target_command
    else:
        command = ["ssh", ssh_host, "bash -l -c " + shlex.quote(" ".join(shlex.quote(arg) for arg in target_command))]

    logger.info(f"Running command: {' '.join(command)}")
    output = subprocess.run(command, stdout=subprocess.PIPE, text=True, check=True)
    stringio = io.StringIO(output.stdout)
    df = pl.read_csv(stringio, separator="\t")
    df = df.rename({"JOBID": "job_id", "NAME": "name", "NODELIST": "node_list"})
    string_id_expr = pl.col("name").str.extract(r"WU(\d+)")
    return df.with_columns(workunit_id=pl.when(string_id_expr.is_not_null()).then(string_id_expr.cast(int)))


def get_workunit_status(client: Bfabric, workunit_ids: list[int]) -> dict[int, str]:
    """Returns the status of the workunits with the specified ids, by consoluting the bfabric API.
    If a workunit was deleted, but it is in the slurm queue, it will be considered a zombie.
    """
    workunits = Workunit.find_all(ids=workunit_ids, client=client)
    return {id: workunits[id].data_dict["status"] if id in workunits else "ZOMBIE" for id in workunit_ids}


def find_zombie_jobs(client: Bfabric, partition: str, ssh_host: str | None) -> pl.DataFrame:
    """Checks the status of the slurm jobs in the specified partition, and returns the ones that are zombies."""
    slurm_jobs = get_slurm_jobs(partition=partition, ssh_host=ssh_host)
    if slurm_jobs.is_empty():
        return pl.DataFrame()
    workunit_status = get_workunit_status(
        client=client, workunit_ids=slurm_jobs["workunit_id"].drop_nulls().cast(int).to_list()
    )
    workunit_status_table = pl.from_dict(dict(workunit_id=workunit_status.keys(), status=workunit_status.values()))
    logger.info(slurm_jobs.join(workunit_status_table, on="workunit_id", how="left").sort("workunit_id"))
    logger.info(f"Active jobs: {workunit_status_table.height}")
    logger.info(f"Found {workunit_status_table.filter(pl.col('status') == 'ZOMBIE').height} zombie jobs.")
    return workunit_status_table.filter(pl.col("status") == "ZOMBIE")


def main() -> None:
    """Checks the status of the slurm jobs in the specified partition, and reports if there are any zombies."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--partition", type=str, default="prx")
    parser.add_argument("--ssh", type=str, default=None, help="SSH into the given node to obtain list.")
    args = parser.parse_args()
    client = Bfabric.from_config()
    zombie_jobs = find_zombie_jobs(client, partition=args.partition, ssh_host=args.ssh)
    print(json.dumps(zombie_jobs["workunit_id"].to_list()))
    if not zombie_jobs.is_empty():
        sys.exit(1)


if __name__ == "__main__":
    main()

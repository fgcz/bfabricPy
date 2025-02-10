from __future__ import annotations

import argparse
import io
import json
import shlex
import subprocess

import polars as pl
import sys
from loguru import logger

from bfabric import Bfabric
from bfabric.entities import Workunit, Application
from bfabric.utils.cli_integration import use_client


def get_slurm_jobs(partition: str, ssh_host: str | None) -> pl.DataFrame:
    """Returns the active slurm jobs from the specified partition, if it is intended to be run remotely the
    ssh host can be specified.
    """
    target_command = ["squeue", "-p", partition, "--format=%i\t%j\t%N"]
    if ssh_host is None:
        command = target_command
    else:
        command = [
            "ssh",
            ssh_host,
            "bash -l -c " + shlex.quote(" ".join(shlex.quote(arg) for arg in target_command)),
        ]

    logger.info(f"Running command: {shlex.join(command)}")
    output = subprocess.run(command, stdout=subprocess.PIPE, text=True, check=True)
    stringio = io.StringIO(output.stdout)
    df = pl.read_csv(stringio, separator="\t")
    df = df.rename({"JOBID": "job_id", "NAME": "name", "NODELIST": "node_list"})
    string_id_expr = pl.col("name").str.extract(r"WU(\d+)")
    return df.with_columns(workunit_id=pl.when(string_id_expr.is_not_null()).then(string_id_expr.cast(int)))


def get_workunit_infos(client: Bfabric, workunit_ids: list[int]) -> list[dict[str, str]]:
    """Retrieves information about the workunits with the specified ids.
    If a workunit was deleted, but it is in the slurm queue, it will be considered a zombie.
    """
    # Find the workunits which actually exist.
    workunits = Workunit.find_all(ids=workunit_ids, client=client)

    # Retrieve application id -> name mapping.
    app_ids = {wu["application"]["id"] for wu in workunits.values()}
    apps = Application.find_all(ids=list(app_ids), client=client)
    app_names = {app["id"]: app["name"] for app in apps.values()}

    return [
        {
            "workunit_id": id,
            "status": (workunits[id].data_dict["status"] if id in workunits else "ZOMBIE"),
            "application_name": (app_names[workunits[id]["application"]["id"]] if id in workunits else "N/A"),
        }
        for id in workunit_ids
    ]


def find_zombie_jobs(client: Bfabric, partition: str, ssh_host: str | None) -> pl.DataFrame:
    """Checks the status of the slurm jobs in the specified partition, and returns the ones that are zombies."""
    slurm_jobs = get_slurm_jobs(partition=partition, ssh_host=ssh_host)
    if slurm_jobs.is_empty():
        return pl.DataFrame()
    workunit_info_table = pl.DataFrame(
        get_workunit_infos(
            client=client,
            workunit_ids=slurm_jobs["workunit_id"].drop_nulls().cast(int).to_list(),
        )
    )
    pl.Config.set_tbl_rows(100)
    logger.info(slurm_jobs.join(workunit_info_table, on="workunit_id", how="left").sort("workunit_id"))
    logger.info(f"Active jobs: {workunit_info_table.height}")
    logger.info(f"Found {workunit_info_table.filter(pl.col('status') == 'ZOMBIE').height} zombie jobs.")
    return workunit_info_table.filter(pl.col("status") == "ZOMBIE")


@use_client
def main(*, client: Bfabric) -> None:
    """Checks the status of the slurm jobs in the specified partition, and reports if there are any zombies."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--partition", type=str, default="prx")
    parser.add_argument("--ssh", type=str, default=None, help="SSH into the given node to obtain list.")
    args = parser.parse_args()
    zombie_jobs = find_zombie_jobs(client, partition=args.partition, ssh_host=args.ssh)
    if zombie_jobs.is_empty():
        print(json.dumps([]))
    else:
        print(json.dumps(zombie_jobs["workunit_id"].to_list()))
        sys.exit(1)


if __name__ == "__main__":
    main()

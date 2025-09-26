#!/usr/bin/env python3

"""
Author:
     Maria d'Errico <maria.derrico@fgcz.ethz.ch>

     Feb 2023

Description:
 The following script automatically creates an analysis workflow step given a workunit id.
 i.e. if the Maxquant workunit 285507 is given, a workflow step Maxquant is created
 (see https://fgcz-bfabric.uzh.ch/bfabric/workunit/show.html?id=285507&tab=workflowsteps)
 More details: https://fgcz-bfabric.uzh.ch/bfabric/workunit/show.html?id=285507&tab=comments
 See workflowtemplatestep_ids for the currently enabled apps.

Usage: bfabric_save_workflowstep.py 285507
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import yaml
from pydantic import BaseModel

from bfabric import Bfabric
from bfabric.entities import Workunit


def _get_user_id(login: str, client: Bfabric) -> int | None:
    result = client.read("user", {"login": login}, return_id_only=True)
    if len(result) == 1:
        return result[0]["id"]
    else:
        raise RuntimeError(f"Could not find user with login: {login}")


class SaveWorkflowStepConfig(BaseModel):
    template_step_ids: dict[int, int]
    template_ids: dict[int, int]


def save_workflowstep(workunit_id: int, config: SaveWorkflowStepConfig) -> None:
    """Creates an analysis workflow step for a given workunit id."""
    client = Bfabric.connect()

    workflowtemplatestep_ids = config.template_step_ids
    workflowtemplate_ids = config.template_ids

    workunit = Workunit.find(id=workunit_id, client=client)
    user_id = _get_user_id(login=workunit["createdby"], client=client)

    application_id = workunit["application"]["id"]
    container_id = workunit["container"]["id"]

    if application_id in workflowtemplatestep_ids and application_id in workflowtemplate_ids:
        workflows = client.read("workflow", obj={"containerid": container_id}).to_list_dict()
        # if workflows is None, no workflow is available - > create a new one
        workflow_id = -1
        if workflows:
            # check if the corresponding workflow exists (template id 59)
            for item in workflows:
                if item["workflowtemplate"]["id"] == workflowtemplate_ids[application_id]:
                    workflow_id = item["id"]
                    break
        # case when no workflows are available (workflows == None)
        if workflow_id == -1:
            res = client.save(
                "workflow",
                obj={
                    "containerid": container_id,
                    "workflowtemplateid": workflowtemplate_ids[application_id],
                },
            )
            workflow_id = res[0]["id"]

        res = client.save(
            "workflowstep",
            obj={
                "workflowid": workflow_id,
                "workflowtemplatestepid": workflowtemplatestep_ids[application_id],
                "workunitid": workunit_id,
                "supervisorid": user_id,
            },
        )
        print(res[0])


def main() -> None:
    """Parses command line args and calls `save_workflowstep`."""
    parser = argparse.ArgumentParser(description="Create an analysis workflow step")
    parser.add_argument("workunitid", metavar="workunitid", type=int, help="workunit id")
    parser.add_argument(
        "--config-path",
        default=Path(os.path.expanduser("~/slurmworker/config/legacy_workflow_steps.yml")),
        type=Path,
        required=False,
    )
    args = parser.parse_args()
    config = SaveWorkflowStepConfig.model_validate(yaml.safe_load(args.config_path.read_text()))
    save_workflowstep(workunit_id=args.workunitid, config=config)


if __name__ == "__main__":
    main()

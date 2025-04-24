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

from bfabric import Bfabric


def save_workflowstep(workunit_id: int | None = None) -> None:
    """Creates an analysis workflow step for a given workunit id."""
    client = Bfabric.connect()
    workflowtemplatestep_ids = {
        224: 247,  # MaxQuant
        # 295: 248, # FragPipe-RESOURCE
        314: 254,  # DIANN
        255: 256,  # maxquant_scaffold
        266: 258,  # MaxQuant-sampleSizeEstimation
    }
    workflowtemplate_ids = {
        224: 59,  # Proteomics Data analysis
        # 295: 59,
        314: 59,
        255: 60,  # Proteomics Results
        266: 60,
    }

    workunit = client.read("workunit", obj={"id": workunit_id}).to_list_dict()[0]
    application_id = workunit["application"]["id"]
    container_id = workunit["container"]["id"]

    if application_id in workflowtemplatestep_ids and application_id in workflowtemplate_ids:
        workflows = client.read("workflow", obj={"containerid": container_id}).to_list_dict()
        # if workflows is None, no workflow is available - > create a new one
        daw_id = -1
        if workflows:
            # check if the corresponding workflow exists (template id 59)
            for item in workflows:
                if item["workflowtemplate"]["id"] == workflowtemplate_ids[application_id]:
                    daw_id = item["id"]
                    break
        # case when no workflows are available (workflows == None)
        if daw_id == -1:
            daw = client.save(
                "workflow",
                obj={
                    "containerid": container_id,
                    "workflowtemplateid": workflowtemplate_ids[application_id],
                },
            )
            daw_id = daw[0]["id"]

        res = client.save(
            "workflowstep",
            obj={
                "workflowid": daw_id,
                "workflowtemplatestepid": workflowtemplatestep_ids[application_id],
                "workunitid": workunit_id,
            },
        )
        print(res[0])


def main() -> None:
    """Parses command line args and calls `save_workflowstep`."""
    parser = argparse.ArgumentParser(description="Create an analysis workflow step")
    parser.add_argument("workunitid", metavar="workunitid", type=int, help="workunit id")
    args = parser.parse_args()
    save_workflowstep(workunit_id=args.workunitid)


if __name__ == "__main__":
    main()

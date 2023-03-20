#!/usr/bin/python3

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

import sys
from bfabric import Bfabric



def main(workunit_id = None):
    B = Bfabric()
    workflowtemplatestep_ids = {224: 247, # MaxQuant
                 #295: 248, # FragPipe-RESOURCE
                 314: 254, # DIANN
                 255: 256, # maxquant_scaffold
                 266: 258  # MaxQuant-sampleSizeEstimation
                 }
    workflowtemplate_ids = {224: 59, # Proteomics Data analysis
               #295: 59,
               314: 59,
               255: 60, # Proteomics Results
               266: 60
               }

    workunit = B.read_object("workunit", obj={"id": workunit_id})[0]
    application_id = workunit["application"]["_id"]
    container_id = workunit["container"]["_id"]

    if application_id in workflowtemplatestep_ids and application_id in workflowtemplate_ids:
        workflows = B.read_object("workflow", obj={"containerid": container_id})
        # if workflows is None, no workflow is available - > create a new one
        daw_id = -1
        if workflows is not None:
            # check if the corresponding workflow exists (template id 59)
            for item in workflows:
                if item["workflowtemplate"]["_id"] == workflowtemplate_ids[application_id]:
                    daw_id = item["_id"]
                    break
        else:
            pass
        # case when no workflows are available (workflows == None)
        if daw_id == -1:
            daw = B.save_object("workflow", obj={"containerid": container_id, "workflowtemplateid": workflowtemplate_ids[application_id]})
            daw_id = daw[0]["_id"]

        res = B.save_object("workflowstep", obj = {"workflowid": daw_id, "workflowtemplatestepid": workflowtemplatestep_ids[application_id], "workunitid": workunit_id})
        print(res[0])
    else:
        pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Create an analysis workflow step')
    parser.add_argument('workunitid', metavar='workunitid', type=int,
            help='workunit id')
    args = parser.parse_args()
    main(workunit_id = args.workunitid)


#!/usr/bin/python3

"""
Author:
     Maria d'Errico <maria.derrico@fgcz.ethz.ch>


Description:
 The following script gets a csv file as input and automatically
 generates a json structure with attributes accepted by B-Fabric for 
 the creation of datasets.

 Example of input file:
  attr1, attr2
  "1", "1"
  "2", "2"

 Example of json output:
  obj['attribute'] = [ {'name':'attr1', 'position':1},
                       {'name':'attr2', 'position':2} ]
  obj['item'] = [ {'field': [{'value': 1, 'attributeposition':1},
                             {'value': 1,  'attributeposition':2 }],
                   'position':1},
                  {'field': [{'value': 2, 'attributeposition':1},
                          {'value': 2,  'attributeposition':2 }],
                   'position':2}]

Usage: bfabric_save_csv2dataset.py [-h] --csvfile CSVFILE --name NAME --containerid int [--workunitid int]
"""

import sys
from bfabric import Bfabric



def main(workunit_id = None):
    B = Bfabric()
    workflowtemplatestep_ids = {224: 247 # MaxQuant
                 #295: 248, # FragPipe-RESOURCE
                 #314: 254, # DIANN
                 #255: 256, # maxquant_scaffold
                 #266: 258  # MaxQuant-sampleSizeEstimation
                 }
    workflowtemplate_ids = {224: 59 # Proteomics Data analysis
               #295: 59,
               #314: 59,
               #255: 60, # Proteomics Results
               #266: 60
               }

    workunit = B.read_object("workunit", obj={"id": workunit_id})[0]
    application_id = workunit["application"]["_id"]
    container_id = workunit["container"]["_id"]

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


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Create an analysis workflow step')
    parser.add_argument('workunitid', metavar='workunitid', type=int,
            help='workunit id')
    args = parser.parse_args()
    main(workunit_id = args.workunitid)


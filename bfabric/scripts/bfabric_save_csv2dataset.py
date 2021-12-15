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
import csv 

def csv2json(csvFilePath):
    obj = {}
    obj["item"] = []
    obj["attribute"] = []
    types = {int: "Integer", str: "String", float: "Float"}
    # Open the csv file in read mode and create a file object
    with open(csvFilePath, encoding='utf-8') as csv_file:
        # Creating the DictReader iterator
        csv_reader = csv.DictReader(csv_file)
        nrow = 0
        # Read individual rows of the csv file as a dictionary
        for row in csv_reader:
            nrow = nrow + 1
            fields = []
            for attr in range(0, len(list(row.keys()))):
                if nrow == 1:
                    # Fill in attributes info
                    attr_type = type(list(row.values())[attr])
                    entry = {"name": list(row.keys())[attr], "position": attr+1,
                            "type": types[attr_type]}
                    obj["attribute"].append(entry)
                else:
                    pass
                # Fill in values info
                field = {"attributeposition": attr+1,
                        "value": list(row.values())[attr]}
                fields.append(field)
            item = {"field": fields, "position": nrow} 
            obj["item"].append(item)
    return(obj)

def main(csv_file, dataset_name, container_id, workunit_id = None):
    bfapp = Bfabric()
    obj = csv2json(csv_file)
    obj['name'] = dataset_name
    obj['containerid'] = container_id
    if workunit_id is not None:
        obj['workunitid'] = workunit_id
    else:
        pass
    endpoint = 'dataset'
    res = bfapp.save_object(endpoint=endpoint, obj=obj)
    print(res[0])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Create a B-Fabric dataset')
    parser.add_argument('--csvfile', required=True,
            help='the path to the csv file to be uploaded as dataset')
    parser.add_argument('--name', required=True,
            help='dataset name as a string')
    parser.add_argument('--containerid', metavar='int', required=True,
            help='container id')
    parser.add_argument('--workunitid', metavar='int', required=False,
            help='workunit id')
    args = parser.parse_args()
    if args.workunitid is None:
        main(csv_file = args.csvfile, dataset_name = args.name, container_id = args.containerid)
    else:
        main(csv_file = args.csvfile, dataset_name = args.name, container_id = args.containerid,
                workunit_id = args.workunitid)


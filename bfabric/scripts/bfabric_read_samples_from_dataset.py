#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
Author:
    Maria d'Errico <maria.derrico@fgcz.ethz.ch>
    13.03.2023

Description:
    The script returns the sample id for each resource in the dataset provided as input

Input: dataset id

Output: list of sample id

Usage:
   bfabric_read_samples_from_dataset.py datasetid
"""

import sys
import os
import csv
import bfabric



B = bfabric.Bfabric()

def read_dataset(dataset_id):
    ds = B.read_object(endpoint="dataset", obj={'id': dataset_id})[0]
    return ds

def get_table(relativepath):
    res = B.read_object(endpoint='resource', obj={'relativepath': relativepath})[0]
    sample = B.read_object(endpoint='sample', obj={'id': res.sample._id})[0]
    try:
        groupingvar = sample.groupingvar.name
    except:
        groupingvar = ""
        pass
    return res.workunit._id, res._id, res.name, sample.name, groupingvar


def run(dataset_id):
    ds = read_dataset(dataset_id)
    attributeposition = [x.position for x in ds.attribute if x.name == "Relative Path"][0]
    print ("{}\t{}\t{}\t{}\t{}".format('workunit.id', 'inputresource.id', 'inputresource.name', 'sample.name', 'groupingvar.name'))
    for i in ds.item:
        for x in i.field:
            if hasattr(x, "value") and x.attributeposition == attributeposition:
                workunitid, resourceid, resourcename, samplename, groupingvar = get_table(x.value)
                print ("{}\t{}\t{}\t{}\t{}".format(workunitid, resourceid, resourcename, samplename, groupingvar))


if __name__ == "__main__":
    dataset_id = int(sys.argv[1])
    run(dataset_id)


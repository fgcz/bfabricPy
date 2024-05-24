#!/usr/bin/env python3
# -*- coding: latin1 -*-

import sys
import os
import yaml
from optparse import OptionParser
import bfabric
import csv
import re

"""
    customattribute[] =
      (xmlCustomAttribute){
         name = "Age0"
         value = "49"
         type = "String"
      },

"""
bf = bfabric.Bfabric(verbose=False)


def annotate(sampleid=None, name=None, value=None):
    res = bf.read_object(endpoint="sample", obj={"id": sampleid})

    try:
        customattribute = res[0].customattribute
        for a in customattribute:
            if a.name.lower() == name.lower():
                print("{} already defined".format(a.name))
                return
    except:
        # there are no customattributes defined yet
        customattribute = []

    customattribute.append({"name": "{}".format(name), "value": "{}".format(value)})
    res = bf.save_object(endpoint="sample", obj={"id": sampleid, "customattribute": customattribute})

    print(res[0])


def process(filename="/Users/cp/Desktop/annotation.csv", tryrun=True):
    with open(filename) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",")
        count = 0
        for row in csv_reader:
            if count == 0:
                colnames = row
            else:
                # print("{}\t{}".format(count, row))
                x = re.search(".*_[sS]([0-9]+)_.+", row[0])
                if x is not None:
                    print("sampleID={sample}".format(sample=x.group(1)))
                    for idx in range(1, len(row)):
                        print("\t{}={}".format(colnames[idx], row[idx]))
                        if tryrun is False:
                            annotate(sampleid=x.group(1), name=colnames[idx], value=row[idx])
            count = count + 1


if __name__ == "__main__":
    process(tryrun=False)

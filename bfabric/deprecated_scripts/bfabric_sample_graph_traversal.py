#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
travers the bfabric sample graph
input: resource id (sample id)

output: FragPipe required TMT settings

usage:
   bfabric_sample_graph_traversal.py 449326  
"""

import sys
import os
import csv
import bfabric

from random import randint
from time import sleep


class SampleGraph:

    B = bfabric.Bfabric()

    # use as stack for the DFS
    L = []

    # keeps the visited sample ids
    VISITED = []

    # fragpipe-manifest
    # key is resource id and the value is a list experiments
    manifest = {}

    # annotation.txt
    # data structure for keeping annotation.txt infos (de-multiplexed data) containing the tagging
    # annotation = {}

    links = {}

    def __init__(self, annotation_template):
        self.annotation_template = annotation_template
        self.annotation = {}

    def read_dataset(self, dataset_id):
        ds = self.B.read_object(endpoint="dataset", obj={"id": dataset_id})[0]
        return ds

    def get_sampleID(self, relativepath):
        res = self.B.read_object(endpoint="resource", obj={"relativepath": relativepath})[0]
        print("\t{} -> {}".format(res.sample._id, res._id))
        return res.sample._id

    def traverse(self, childSampleId):
        """
        fill up the internal data structure
        for producing the manifest and annotation.txt files for each exp.
        """
        res = self.B.read_object(endpoint="sample", obj={"id": childSampleId})
        childSample = res[0]

        if "multiplexid" in childSample:
            # in this special case we reached last level keeping the tag
            print(
                """\t{} [shape=box label="{}\\n{}"];""".format(
                    childSample._id, childSample._id, childSample.multiplexid
                )
            )
            try:
                self.annotation[childSample.multiplexid] = childSample.parent[0]._id
            except:
                print(
                    "multiplexid {} for sample {} not in the annotation file template".format(
                        childSample.multiplexid, childSample._id
                    )
                )

        if "parent" in childSample:
            self.links[childSampleId] = [x._id for x in childSample.parent]
            for parent in childSample.parent:
                print("\t{} -> {}".format(parent._id, childSampleId))
                if not parent._id in self.VISITED:
                    self.VISITED.append(parent._id)
                    self.L.append(parent._id)

        # print("\t# DEBUG = {}".format(len(self.L)))

        while len(self.L) > 0:
            u = self.L[0]
            self.L.remove(u)
            self.traverse(u)

    def run(self, dataset_id):
        ds = self.read_dataset(dataset_id)
        attributeposition = [x.position for x in ds.attribute if x.name == "Relative Path"][0]
        for i in ds.item:
            for x in i.field:
                if hasattr(x, "value") and x.attributeposition == attributeposition:
                    print("# relativepath = {}".format(x.value))
                    sampleID = self.get_sampleID(x.value)
                    print("# inputSampleId = {}".format(sampleID))
                    self.annotation = self.annotation_template
                    self.traverse(sampleID)
                    experiment = self.links[sampleID]
                    if len(experiment) == 1:
                        self.write_annotation(experiment[0])
                        self.write_manifest(x.value, experiment[0])
                    else:
                        print(
                            "# Wrong inputSampleId, please check the sample ID {}, it should be after fractionation".format(
                                sampleID
                            )
                        )

    def write_annotation(self, experiment):
        dirname = str(experiment)
        if not os.path.isdir(dirname):
            print("# creating directory {}".format(dirname))
            os.makedirs(dirname)
            with open("./" + dirname + "/annotation.txt", "w") as f:
                w = csv.writer(f, delimiter="\t")
                w.writerows(self.annotation.items())
        else:
            pass

    def write_manifest(self, resource, experiment):
        filename = "manifest.fp-manifest"
        pathtoresource = os.getcwd() + "/" + os.path.basename(resource)
        if not os.path.exists(filename):
            with open(filename, "w") as f:
                line = "\t".join([pathtoresource, str(experiment), "", "", "DDA"]) + "\n"
                f.write(line)
        else:
            with open(filename, "a") as f:
                line = "\t".join([pathtoresource, str(experiment), "", "", "DDA"]) + "\n"
                f.write(line)


if __name__ == "__main__":

    dataset_id = 44384  # int(sys.argv[1])

    infile = open(sys.argv[1], "r")
    annotation_template = {}
    for line in infile:
        line = line.strip()
        content = line.split(" ", 1)
        annotation_template.update({content[0]: content[1]})
    infile.close()

    # constructor
    print("""digraph G{\n\trankdir="LR";""")
    G = SampleGraph(annotation_template)
    G.run(dataset_id)
    # for s in [461042, 461041, 461017]:
    #    G.annotation = G.annotation_template.copy()
    #    G.traverse(s)
    #    G.write_annotation(s)
    #    print("# {}".format(G.annotation))
    #    print("# {}".format(G.annotation_template))
    # print("# {}".format(G.links))

    print("""}""")


"""
sample output having the TMT TAG
(xmlSample){
   _id = 460998
   _classname = "sample"
   deletable = "true"
   updatable = "true"
   created = "2023-02-07 08:39:26"
   createdby = "tobiasko"
   modified = "2023-02-07 08:39:26"
   modifiedby = "tobiasko"
   name = "Labeled_460978"
   child[] =
      (xmlSample){
         _id = 461017
         _classname = "sample"
      },
   container =
      (xmlContainer){
         _id = 30781
         _classname = "order"
      }
   multiplexid = "127C"
   multiplexkit = "TMT10"
   parent[] =
      (xmlSample){
         _id = 460978
         _classname = "sample"
      },
   tubeid = "o30781/2"
   type = "Labeled MS Sample - Proteomics"
 }
"""

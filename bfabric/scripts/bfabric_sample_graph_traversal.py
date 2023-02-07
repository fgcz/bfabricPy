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

    # annimation.txt
    # data structure for keeping annotation.txt infors (de-multiplexed data) containing the tagging
    annotation = {}

    def init(self):
        pass

    def traverse(self, childSampleId):
        """
        fill up the internal data structure
        for producing the manifest and annotation.txt files for each exp.


        TODO: when to we populate the table? now or later?
        """
        res = self.B.read_object(endpoint='sample', obj={'id': childSampleId}, page=1)
        childSample = res[0]

        if "multiplexid" in  childSample:
            # in this special case we reached last level keeping the tag
            print ("\t# {} {}".format(childSample._id, childSample.multiplexid))

        if 'parent' in childSample:
            self.annotation[childSampleId] = [x._id for x in childSample.parent]
            for parent in res[0].parent:
                if not parent._id in self.VISITED:
                    print("\t{} -> {}".format(parent._id, childSampleId))
                    self.VISITED.append(parent._id)
                    self.L.append(parent._id)

        print("\t# DEBUG = {}".format(len(self.L)))

        while (len(self.L) > 0):
            u = self.L[0]
            self.L.remove(u)
            self.traverse(u)

    def run(self, inputResource):
        for resourceId in inputResource:
            # sampleId = getSampleOfResource(resourceId)
            # traverse(sampleId)
            pass

    def writetable(self, childSampleID):
        MSsample = self.annotation[childSampleID][0]
        print(childSampleID, MSsample)
        print(MSsample, self.annotation[MSsample])
        print (self.annotation)

        
if __name__ == "__main__":

    # TODO(cp): read WU12345.yaml file

    # constructor
    G = SampleGraph()

    # TODO(cp): G.run(listOfResources)
    if len(sys.argv) > 1:
        G.traverse(int(sys.argv[1]))


    G.writetable(int(sys.argv[1]))



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

#!/usr/bin/env python
# -*- coding: latin1 -*-

"""
travers the bfabric sample graph
input: resource id (sample id)

output: FragPipe required TMT settings
"""

import sys
import bfabric

from random import randint
from time import sleep

B = bfabric.Bfabric()

L = []
VISITED = []

def __sample_dfs (sampleid):
   res = B.read_object(endpoint='sample', obj={'id': sampleid} , page=1)

   if 'parent' in res[0]:
       for s in res[0].parent:
           if not s._id in VISITED:
               print("\t{} -> {}".format(sampleid, s._id))
               VISITED.append(s._id)
               L.append(s._id)

   print("DEBUG = {}".format(len(L)))
   while (len(L) > 0):
       u = L[0]
       L.remove(u)
       __sample_dfs(u)

        
if __name__ == "__main__":
    if len(sys.argv) > 1:
        __sample_dfs(int(sys.argv[1]))


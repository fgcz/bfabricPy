#!/usr/bin/python3

"""
Author:
  Witold Wolski

Description:
  get created by user name

"""

import bfabric
import sys

workunitid = sys.argv[1]
res = bfabric.Bfabric(verbose=False).read_object(endpoint="workunit", obj={'id': workunitid})
created_by = res[0].createdby
print(created_by)



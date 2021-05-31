#!/usr/bin/python
# -*- coding: latin1 -*-

"""

Copyright (C) 2021 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Maria d'Errico <mderrico@fgcz.ethz.ch>

Licensed under  GPL version 3


"""

import os
import sys
import bfabric
import datetime

def usage():
    print("usage:\n")
    msg = "\t{} <workunitID> <attribute> <value>".format(sys.argv[0])
    print(msg)

if __name__ == "__main__":
    B = bfabric.Bfabric()

    query_obj = {}

    try:
        workunitID = sys.argv[1]
        attribute = sys.argv[2]
        value = sys.argv[3]
        query_obj["id"] = workunitID
        query_obj[attribute] = value
    except:
        usage()
        sys.exit(1)
    

    res = B.save_object(endpoint='workunit', obj=query_obj)
    print(res)

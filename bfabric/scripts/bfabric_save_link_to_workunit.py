#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
Copyright (C) 2023 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Christian Panse <cp@fgcz.ethz.ch> 20231011
"""

import sys
import os
from bfabric import Bfabric

def save_link(wuid=294156, link="", name=""):
    B = Bfabric()

    rv = B.save_object('link',
        obj={'name': name,
            'parentclassname': 'workunit',
            'parentid': wuid,
            'url': link})
    B.print_json(rv)

if __name__ == "__main__":
    if len(sys.argv) == 4:
        save_link(wuid=sys.argv[1], link=sys.argv[2], name=sys.argv[3])
    else:
        print ("Usage:")
        print ("{} <workunit id> <link> <name>".format(sys.argv[0]))
        print ("Example:")
        print ("{} 294156 'https://fgcz-shiny.uzh.ch/exploreDE_prot/?data=p3000/bfabric/Proteomics/SummarizedExperiment/2023/2023-09/2023-09-29/workunit_294156/2363303.rds' 'demo1 link'".format(sys.argv[0]))


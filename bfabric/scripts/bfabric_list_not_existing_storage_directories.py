#!/usr/bin/python3
# -*- coding: latin1 -*-

"""
Copyright (C) 2020 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Maria d'Errico <maria.derrico@fgcz.ethz.ch>
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

http://fgcz-bfabric.uzh.ch/bfabric/executable?wsdl
"""
import os


import bfabric
B = bfabric.Bfabric()

ROOTDIR="/srv/www/htdocs/"

def listNotExistingStorageDirs():
    rv = B.read_object('sample', {'type': '%Biological Sample%'})
    containerIDs = list(set(map(lambda x: x.container._id, rv)))

    for cid in containerIDs:
        if not os.path.isdir("{}/p{}".format(ROOTDIR, cid)):
            print (cid)


listNotExistingStorageDirs()

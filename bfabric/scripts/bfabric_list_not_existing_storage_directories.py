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

def listNotExistingStorageDirs(technologyid=2):
    rv = B.read_object('container', {'technologyid': technologyid})
    containerIDs = list(set(map(lambda x: x._id, rv)))


    for cid in containerIDs:
        if not os.path.isdir(f"{ROOTDIR}/p{cid}"):
            print (cid)


listNotExistingStorageDirs(technologyid=2)
listNotExistingStorageDirs(technologyid=4)

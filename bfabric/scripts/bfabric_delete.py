#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""

Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_delete.py $
$Id: bfabric_delete.py 2525 2016-10-17 09:52:59Z cpanse $ 



http://fgcz-bfabric.uzh.ch/bfabric/executable?wsdl

"""
import argparse
import bfabric
from bfabric.bfabric2 import Bfabric, get_system_auth


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("endpoint", help="endpoint", choices=bfabric.endpoints)
    parser.add_argument("id", help="id", type=int)
    args = parser.parse_args()
    client = Bfabric(*get_system_auth())
    res = client.delete(endpoint=args.endpoint, id=args.id).to_list_dict()
    for i in res:
        print(i)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
set status of a resource of a given resource id
"""
import argparse

from bfabric.bfabric2 import Bfabric

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/fgcz_bfabric_setResourceStatus_available.py $
# $Id: fgcz_bfabric_setResourceStatus_available.py 2397 2016-09-06 07:04:35Z cpanse $


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("resource_id", type=int, help="resource id", nargs="+")
    args = parser.parse_args()
    client = Bfabric.from_config(verbose=True)
    for resource_id in args.resource_id:
        try:
            res = client.save("resource", {"id": resource_id, "status": "available"})
            print(res)
        except Exception:
            print("failed to set resourceid {} 'available'.".format(resource_id))
            raise


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
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
import json

from bfabric import Bfabric


def bfabric_delete(endpoint: str, id: int) -> None:
    """Deletes the object with id `id` from the `endpoint`."""
    client = Bfabric.from_config(verbose=True)
    res = client.delete(endpoint=endpoint, id=id).to_list_dict()
    print(json.dumps(res, indent=2))


def main() -> None:
    """Parses arguments and calls `bfabric_delete`."""
    parser = argparse.ArgumentParser()
    parser.add_argument("endpoint", help="endpoint", choices=bfabric.endpoints)
    parser.add_argument("id", help="id", type=int)
    args = parser.parse_args()
    bfabric_delete(args.endpoint, args.id)


if __name__ == "__main__":
    main()

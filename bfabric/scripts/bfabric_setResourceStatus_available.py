#!/usr/bin/env python3
"""
set status of a resource of a given resource id
"""
from __future__ import annotations

import argparse

from bfabric import Bfabric


# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#


def set_resource_status_available(client: Bfabric, resource_id: list[int]) -> None:
    """Sets the status of the specified resources to 'available'."""
    for resource_id in resource_id:
        try:
            res = client.save("resource", {"id": resource_id, "status": "available"}).to_list_dict()
            print(res)
        except Exception:
            print(f"failed to set resourceid {resource_id} 'available'.")
            raise

def main() -> None:
    """Parses command line arguments and calls `set_resource_status_available`."""
    parser = argparse.ArgumentParser()
    parser.add_argument("resource_id", type=int, help="resource id", nargs="+")
    args = parser.parse_args()
    client = Bfabric.from_config(verbose=True)
    set_resource_status_available(client, args.resource_id)


if __name__ == "__main__":
    main()

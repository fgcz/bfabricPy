#!/usr/bin/env python3
"""
set status of a resource of a given resource id
"""

from __future__ import annotations

import argparse

import time
from rich.pretty import pprint

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client
from bfabric_scripts.feeder.report import report_resource


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
        time.sleep(5)
        try:
            res = report_resource(client=client, resource_id=resource_id)
            pprint(res, indent_guides=False)
        except Exception:
            print(f"failed to set resourceid {resource_id} 'available'.")
            raise


@use_client
def main(*, client: Bfabric) -> None:
    """Parses command line arguments and calls `set_resource_status_available`."""
    parser = argparse.ArgumentParser()
    parser.add_argument("resource_id", type=int, help="resource id", nargs="+")
    args = parser.parse_args()
    set_resource_status_available(client, args.resource_id)


if __name__ == "__main__":
    main()

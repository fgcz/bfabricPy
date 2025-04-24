#!/usr/bin/env python3
import argparse
import json

from bfabric import Bfabric


# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#


def main_generic(result_status: str) -> None:
    """Main function for setting workunit status to `result_status`."""
    parser = argparse.ArgumentParser(description=f"Sets workunit status to '{result_status}'")
    parser.add_argument("workunit_id", type=int, help="workunit id")
    args = parser.parse_args()
    client = Bfabric.connect()
    res = client.save("workunit", {"id": args.workunit_id, "status": result_status})
    print(json.dumps(res.to_list_dict(), indent=2))


def main_available() -> None:
    """Calls `main_generic` with 'available' as argument."""
    main_generic("available")


def main_failed() -> None:
    """Calls `main_generic` with 'failed' as argument."""
    main_generic("failed")


def main_processing() -> None:
    """Calls `main_generic` with 'processing' as argument."""
    main_generic("processing")

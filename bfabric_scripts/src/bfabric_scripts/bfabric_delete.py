#!/usr/bin/env python3
"""

Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3
"""

import argparse
import json

from bfabric import Bfabric


def bfabric_delete(client: Bfabric, endpoint: str, id: list[int]) -> None:
    """Deletes the object with id `id` from the `endpoint`."""
    res = client.delete(endpoint=endpoint, id=id).to_list_dict()
    print(json.dumps(res, indent=2))


def main() -> None:
    """Parses arguments and calls `bfabric_delete`."""
    client = Bfabric.from_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("endpoint", help="endpoint", type=str)
    parser.add_argument("id", help="id", type=int, nargs="+")
    args = parser.parse_args()
    bfabric_delete(client=client, endpoint=args.endpoint, id=args.id)


if __name__ == "__main__":
    main()

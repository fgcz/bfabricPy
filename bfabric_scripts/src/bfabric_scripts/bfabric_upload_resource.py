#!/usr/bin/env python3
"""

Copyright (C) 2017,2020 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

this script takes a blob file and a workunit id as input and adds the file as resource to bfabric
"""

import argparse
import json
from pathlib import Path

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client


def bfabric_upload_resource(client: Bfabric, filename: Path, workunit_id: int) -> None:
    """Uploads the specified file to the workunit with the name of the file as resource name."""
    result = client.upload_resource(
        resource_name=filename.name,
        content=filename.read_bytes(),
        workunit_id=workunit_id,
    )
    print(json.dumps(result[0], indent=2))


@use_client
def main(*, client: Bfabric) -> None:
    """Parses the command line arguments and calls `bfabric_upload_resource`."""
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="filename", type=Path)
    parser.add_argument("workunitid", help="workunitid", type=int)
    args = parser.parse_args()
    bfabric_upload_resource(client=client, filename=args.filename, workunit_id=args.workunitid)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# Copyright (C) 2023 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Author:
#   Christian Panse <cp@fgcz.ethz.ch>
from __future__ import annotations

import argparse
from typing import Literal

from bfabric import Bfabric
from bfabric_scripts.cli.api._deprecated_log import write_externaljob, write_workunit
from bfabric.utils.cli_integration import use_client


def bfabric_logthis(
    entity: Literal["externaljob", "workunit"],
    entity_id: int,
    message: str,
    client: Bfabric,
) -> None:
    """Logs a message for an external job."""
    if entity == "externaljob":
        write_externaljob(client=client, externaljob_id=entity_id, message=message)
    else:
        write_workunit(client=client, workunit_id=entity_id, message=message)


@use_client
def main(*, client: Bfabric) -> None:
    """Parses the command line arguments and calls `bfabric_logthis`."""
    parser = argparse.ArgumentParser(description="log message of external job")
    parser.add_argument("entity_id", type=int, help="entity id")
    parser.add_argument("message", type=str, help="message")
    parser.add_argument(
        "--entity",
        type=str,
        choices=["externaljob", "workunit"],
        default="externaljob",
        help="entity type",
    )
    args = vars(parser.parse_args())
    bfabric_logthis(**args, client=client)


if __name__ == "__main__":
    main()

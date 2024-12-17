#!/usr/bin/env python3
# Copyright (C) 2023 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Author:
#   Christian Panse <cp@fgcz.ethz.ch>
from __future__ import annotations

import argparse
from typing import Literal

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric_scripts.cli.api.cli_api_log import write_externaljob, write_workunit


def bfabric_logthis(entity: Literal["externaljob", "workunit"], entity_id: int, message: str) -> None:
    """Logs a message for an external job."""
    setup_script_logging()
    client = Bfabric.from_config()
    if entity == "externaljob":
        write_externaljob(client=client, externaljob_id=entity_id, message=message)
    else:
        write_workunit(client=client, workunit_id=entity_id, message=message)


def main() -> None:
    """Parses the command line arguments and calls `bfabric_logthis`."""
    parser = argparse.ArgumentParser(description="log message of external job")
    parser.add_argument("entity_id", type=int, help="external job id")
    parser.add_argument("message", type=str, help="message")
    parser.add_argument(
        "--entity", type=str, choices=["externaljob", "workunit"], default="externaljob", help="entity type"
    )
    args = vars(parser.parse_args())
    bfabric_logthis(**args)


if __name__ == "__main__":
    main()

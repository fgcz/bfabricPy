#!/usr/bin/env python3
# Copyright (C) 2023 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Author:
#   Christian Panse <cp@fgcz.ethz.ch>
from __future__ import annotations

import argparse

from rich.pretty import pprint

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client


@use_client
def bfabric_logthis(
    externaljob_id: int,
    message: str,
    *,
    client: Bfabric,
) -> None:
    """Logs a message for an external job."""
    pprint({"externaljob_id": externaljob_id, "message": message})
    client.save("externaljob", {"id": externaljob_id, "logthis": message})


def main() -> None:
    """Parses the command line arguments and calls `bfabric_logthis`."""
    parser = argparse.ArgumentParser(description="log message of external job")
    parser.add_argument("externaljob_id", type=int, help="entity id")
    parser.add_argument("message", type=str, help="message")
    args = vars(parser.parse_args())
    bfabric_logthis(**args)


if __name__ == "__main__":
    main()

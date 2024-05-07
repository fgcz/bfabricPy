#!/usr/bin/env python3
# Copyright (C) 2023 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Author:
#   Christian Panse <cp@fgcz.ethz.ch>

import argparse

from bfabric.bfabric2 import Bfabric


def bfabric_logthis(external_job_id: int, message: str) -> None:
    """Logs a message for an external job."""
    client = Bfabric.from_config()
    client.save("externaljob", {"id": external_job_id, "logthis": message})


def main() -> None:
    """Parses the command line arguments and calls `bfabric_logthis`."""
    parser = argparse.ArgumentParser(description="log message of external job")
    parser.add_argument("external_job_id", type=int, help="external job id")
    parser.add_argument("message", type=str, help="message")
    args = vars(parser.parse_args())
    bfabric_logthis(**args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Copyright (C) 2023 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Lists proteomics workunits that are not available on bfabric.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under GPL version 3
"""

from __future__ import annotations

from argparse import ArgumentParser

from bfabric.utils.cli_integration import setup_script_logging
from bfabric_scripts.cli.workunit.not_available import (
    cmd_workunit_not_available,
)


def main() -> None:
    """Parses the command line arguments and calls `list_not_available_proteomics_workunits`."""
    setup_script_logging()
    parser = ArgumentParser(description="Lists proteomics work units that are not available on bfabric.")
    parser.add_argument("--max-age", type=int, help="Max age of work units in days", default=14)
    args = parser.parse_args()
    cmd_workunit_not_available(max_age=args.max_age)


if __name__ == "__main__":
    main()

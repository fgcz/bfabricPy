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
from datetime import datetime, timedelta
from typing import Any

from rich.console import Console
from rich.table import Column, Table

from bfabric import BfabricConfig
from bfabric.bfabric2 import Bfabric


def render_output(workunits_by_status: dict[str, list[dict[str, Any]]], config: BfabricConfig) -> None:
    """Renders the output as a table."""
    table = Table(
        Column("AID", no_wrap=True),
        Column("WUID", no_wrap=True),
        Column("Created", no_wrap=True),
        Column("Status", no_wrap=True),
        Column("Created by", no_wrap=True, max_width=12),
        Column("Name", no_wrap=False),
    )

    for status, workunits in workunits_by_status.items():
        workunits = [x for x in workunits if x["createdby"] not in ["gfeeder", "itfeeder"]]
        status_color = {
            "Pending": "yellow",
            "Processing": "blue",
            "Failed": "red",
        }.get(status, "black")

        for wu in workunits:
            app_url = f"{config.base_url}/application/show.html?id={wu['application']['id']}"
            wu_url = f"{config.base_url}/workunit/show.html?id={wu['id']}&tab=details"
            table.add_row(
                f"[link={app_url}]A{wu['application']['id']:3}[/link]",
                f"[link={wu_url}]WU{wu['id']}[/link]",
                wu["created"],
                f"[{status_color}]{status}[/{status_color}]",
                wu["createdby"],
                wu["name"],
            )

    console = Console()
    console.print(table)


def list_not_available_proteomics_workunits(date_cutoff: datetime) -> None:
    """Lists proteomics work units that are not available on bfabric."""
    client = Bfabric.from_config(verbose=True)
    Console(stderr=True).print(
        f"--- list not available proteomics work units created after {date_cutoff}---",
        style="bright_yellow",
    )

    workunits_by_status = {}
    for status in ["Pending", "Processing", "Failed"]:
        workunits_by_status[status] = client.read(
            endpoint="workunit",
            obj={"status": status, "createdafter": date_cutoff},
        ).to_list_dict()

    render_output(workunits_by_status, config=client.config)


def main() -> None:
    """Parses the command line arguments and calls `list_not_available_proteomics_workunits`."""
    parser = ArgumentParser(description="Lists proteomics work units that are not available on bfabric.")
    parser.add_argument("--max-age", type=int, help="Max age of work units in days", default=14)
    args = parser.parse_args()
    date_cutoff = datetime.today() - timedelta(days=args.max_age)
    list_not_available_proteomics_workunits(date_cutoff)


if __name__ == "__main__":
    main()

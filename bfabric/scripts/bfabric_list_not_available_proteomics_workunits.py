#!/usr/bin/env python3
# -*- coding: latin1 -*-
"""
Copyright (C) 2023 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Lists proteomics workunits that are not available on bfabric.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under GPL version 3
"""

from argparse import ArgumentParser
from datetime import datetime, timedelta

from rich.console import Console
from rich.table import Table

from bfabric.bfabric2 import default_client


def render_output(workunits_by_status):
    """Renders the output as a table."""
    table = Table()
    table.add_column("AID", no_wrap=True)
    table.add_column("WUID", no_wrap=True)
    table.add_column("Created", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Created by", no_wrap=True, max_width=12)
    table.add_column("Name", no_wrap=False)

    for status, workunits in workunits_by_status.items():
        workunits = [x for x in workunits if x["createdby"] not in ["gfeeder", "itfeeder"]]
        status_color = {
            "Pending": "yellow",
            "Processing": "blue",
            "Failed": "red",
        }.get(status, "black")

        for x in workunits:
            app_url = f"https://fgcz-bfabric.uzh.ch/bfabric/application/show.html?id={x['application']['id']}"
            wu_url = f"https://fgcz-bfabric.uzh.ch/bfabric/workunit/show.html?id={x['id']}&tab=details"
            table.add_row(
                f"[link={app_url}]A{x['application']['id']:3}[/link]",
                f"[link={wu_url}]WU{x['id']}[/link]",
                x["created"],
                f"[{status_color}]{status}[/{status_color}]",
                x["createdby"],
                x["name"],
            )

    console = Console()
    console.print(table)


def main():
    """Lists proteomics work units that are not available on bfabric."""
    parser = ArgumentParser(description="Lists proteomics work units that are not available on bfabric.")
    parser.add_argument("--max-age", type=int, help="Max age of work units in days", default=14)
    args = parser.parse_args()
    client = default_client()
    date_cutoff = datetime.today() - timedelta(days=args.max_age)

    Console(stderr=True).print(
        f"--- list not available proteomics work units created after {date_cutoff}---", style="bright_yellow"
    )

    workunits_by_status = {}
    for status in ["Pending", "Processing", "Failed"]:
        workunits_by_status[status] = client.read(
            endpoint="workunit",
            obj={"status": status, "createdafter": date_cutoff},
        ).to_list_dict()

    render_output(workunits_by_status)


if __name__ == "__main__":
    main()

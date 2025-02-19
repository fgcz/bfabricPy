from __future__ import annotations
from datetime import datetime, timedelta
from typing import Iterable

from loguru import logger
from rich.console import Console
from rich.table import Column, Table

from bfabric import Bfabric
from bfabric.entities import Parameter, Workunit, Application
from bfabric.utils.cli_integration import use_client


def render_output(workunits: list[Workunit], client: Bfabric) -> None:
    """Renders the output as a table."""
    table = Table(
        Column("Application", no_wrap=False),
        Column("WU ID", no_wrap=True),
        Column("Created", no_wrap=True),
        Column("Status", no_wrap=True),
        Column("Created by", no_wrap=True, max_width=12),
        Column("Name", no_wrap=False),
        Column("Nodelist", no_wrap=False),
    )

    workunit_ids = [wu.id for wu in workunits]
    app_ids = {wu["application"]["id"] for wu in workunits}

    nodelist_params = Parameter.find_by({"workunitid": workunit_ids, "key": "nodelist"}, client)
    nodelist_values = {param["workunit"]["id"]: param.value for param in nodelist_params.values()}
    application_values = Application.find_all(ids=sorted(app_ids), client=client)

    status_colors = {
        "PENDING": "yellow",
        "PROCESSING": "blue",
        "FAILED": "red",
    }

    for wu in workunits:
        status_color = status_colors.get(wu["status"], "black")
        app = application_values[wu["application"]["id"]]
        table.add_row(
            f"[link={app.web_url}]A{wu['application']['id']:3} {app['name']}[/link]",
            f"[link={wu.web_url}&tab=details]WU{wu['id']}[/link]",
            wu["created"],
            f"[{status_color}]{wu['status']}[/{status_color}]",
            wu["createdby"],
            wu["name"],
            nodelist_values.get(wu.id, "N/A"),
        )

    console = Console()
    console.print(table)


def sort_workunits_by(workunits: Iterable[Workunit], key: str) -> list[Workunit]:
    if key == "status":
        order = ["PENDING", "PROCESSING", "FAILED"]
        return sorted(workunits, key=lambda wu: order.index(wu["status"]))
    elif key in ("application", "app"):
        return sorted(workunits, key=lambda wu: wu["application"]["id"])
    else:
        workunits_list = list(workunits)
        if workunits_list and key in workunits_list[0]:
            return sorted(workunits_list, key=lambda wu: wu[key])
        logger.warning(f"Unknown sort key: {key}")
        return list(workunits)


def filter_workunits_by_user(workunits: list[Workunit], exclude_user: list[str] | None) -> list[Workunit]:
    if exclude_user:
        return [wu for wu in workunits if wu["createdby"] not in exclude_user]
    return workunits


@use_client
def cmd_workunit_not_available(
    *,
    client: Bfabric,
    max_age: float = 14.0,
    sort_by: str = "status",
    exclude_user: list[str] | None = None,
    include_user: list[str] | None = None,
) -> None:
    """Lists not available analysis work units.

    :param max_age: The maximum age of work units in days.
    :param sort_by: The field to sort the output by.
    :param exclude_user: List of users to exclude from the output (implicit default: gfeeder, itfeeder)
    :param include_user: List of users to include in the output
    """
    if exclude_user and include_user:
        raise ValueError("Cannot provide both include and exclude users")

    date_cutoff = datetime.today() - timedelta(days=max_age)
    console = Console()
    with console.capture() as capture:
        console.print(
            f"listing not available proteomics work units created after {date_cutoff}",
            style="bright_yellow",
            end="",
        )
    logger.info(capture.get())

    extra_query = {}
    if include_user:
        extra_query["createdby"] = include_user
    workunits = Workunit.find_by(
        {
            "status": ["Pending", "Processing", "Failed"],
            "createdafter": date_cutoff.isoformat(),
            **extra_query,
        },
        client=client,
    ).values()
    workunits = sort_workunits_by(workunits, sort_by)
    if not include_user and not exclude_user:
        exclude_user = ["gfeeder", "itfeeder"]
    workunits = filter_workunits_by_user(workunits, exclude_user)
    render_output(workunits, client=client)

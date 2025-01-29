from datetime import datetime, timedelta

from loguru import logger
from rich.console import Console
from rich.table import Column, Table

from bfabric import Bfabric
from bfabric.entities import Parameter, Workunit, Application
from bfabric_scripts.cli.base import use_client


def render_output(
    workunits_by_status: dict[str, list[Workunit]], client: Bfabric
) -> None:
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

    workunit_ids = [wu.id for wu_list in workunits_by_status.values() for wu in wu_list]
    app_ids = {
        wu["application"]["id"]
        for wu_list in workunits_by_status.values()
        for wu in wu_list
    }

    nodelist_params = Parameter.find_by(
        {"workunitid": workunit_ids, "key": "nodelist"}, client
    )
    nodelist_values = {
        param["workunit"]["id"]: param.value for param in nodelist_params.values()
    }
    application_values = Application.find_all(ids=sorted(app_ids), client=client)

    for status, workunits_all in workunits_by_status.items():
        workunits = [
            x for x in workunits_all if x["createdby"] not in ["gfeeder", "itfeeder"]
        ]
        status_color = {
            "Pending": "yellow",
            "Processing": "blue",
            "Failed": "red",
        }.get(status, "black")

        for wu in workunits:
            app = application_values[wu["application"]["id"]]
            table.add_row(
                f"[link={app.web_url}]A{wu['application']['id']:3} {app['name']}[/link]",
                f"[link={wu.web_url}&tab=details]WU{wu['id']}[/link]",
                wu["created"],
                f"[{status_color}]{status}[/{status_color}]",
                wu["createdby"],
                wu["name"],
                nodelist_values.get(wu.id, "N/A"),
            )

    console = Console()
    console.print(table)


@use_client
def list_not_available_proteomics_workunits(
    *, client: Bfabric, max_age: float = 14.0
) -> None:
    """Lists not available analysis work units.

    :param max_age: The maximum age of work units in days.
    """
    date_cutoff = datetime.today() - timedelta(days=max_age)
    console = Console()
    with console.capture() as capture:
        console.print(
            f"listing not available proteomics work units created after {date_cutoff}",
            style="bright_yellow",
            end="",
        )
    logger.info(capture.get())

    workunits_by_status = {}
    for status in ["Pending", "Processing", "Failed"]:
        workunits_by_status[status] = Workunit.find_by(
            {"status": status, "createdafter": date_cutoff.isoformat()}, client=client
        ).values()

    render_output(workunits_by_status, client=client)

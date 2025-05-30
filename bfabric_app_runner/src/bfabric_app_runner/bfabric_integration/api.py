"""This module defines some CLI operations without a script, but rather used by directly importing the module."""

import cyclopts

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client

app = cyclopts.App(help="Bfabric app runner integration API commands.")


@app.command
@use_client
def report_failed_workunit(workunit_id: int, *, client: Bfabric) -> None:
    """Sets the status of a workunit to 'failed'."""
    client.save("workunit", {"id": workunit_id, "status": "failed"})


if __name__ == "__main__":
    app()

import cyclopts

from bfabric.cli_formatting import setup_script_logging
from bfabric_scripts.cli.workunit.not_available import list_not_available_proteomics_workunits

app = cyclopts.App()


@app.command
def not_available(max_age: float = 14.0) -> None:
    """Lists not available analysis work units.

    :param max_age: The maximum age of work units in days.
    """
    setup_script_logging()
    list_not_available_proteomics_workunits(max_age=max_age)

import cyclopts

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging

cmd = cyclopts.App(help="write log messages to workunits and external jobs")


@cmd.command
def write_workunit(workunit_id: int, message: str) -> None:
    setup_script_logging()
    client = Bfabric.from_config()
    client.save("workunit", {"id": workunit_id, "progress": message})


@cmd.command
def write_externaljob(externaljob_id: int, message: str) -> None:
    setup_script_logging()
    client = Bfabric.from_config()
    client.save("externaljob", {"id": externaljob_id, "logthis": message})

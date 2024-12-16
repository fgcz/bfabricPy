from typing import Literal, assert_never

import cyclopts

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging

cmd = cyclopts.App(help="write log messages to workunits and external jobs")


@cmd.default
def log_write(entity_type: Literal["workunit", "externaljob"], entity_id: int, message: str) -> None:
    setup_script_logging()
    client = Bfabric.from_config()
    if entity_type == "externaljob":
        client.save("externaljob", {"id": entity_id, "logthis": message})
    elif entity_type == "workunit":
        # TODO this is the old code, not sure if it should set processing as well (but maybe it should for backwards compat?)
        client.save("workunit", {"id": entity_id, "status": "processing", "progress": message})
    else:
        assert_never(entity_type)

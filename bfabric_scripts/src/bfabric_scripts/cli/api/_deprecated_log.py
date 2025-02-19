from __future__ import annotations
from typing import Annotated

import cyclopts
from rich.pretty import pprint

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client

cmd = cyclopts.App(help="DEPRECATED")

log_target = cyclopts.Group(
    "Log Target",
    validator=cyclopts.validators.LimitedChoice(min=1),
)


@cmd.command
@use_client
def write(
    message: str,
    *,
    client: Bfabric,
    workunit: Annotated[int | None, cyclopts.Parameter(group=log_target)] = None,
    externaljob: Annotated[int | None, cyclopts.Parameter(group=log_target)] = None,
) -> None:
    if workunit is not None:
        write_workunit(client=client, workunit_id=workunit, message=message)
    elif externaljob is not None:
        write_externaljob(client=client, externaljob_id=externaljob, message=message)
    else:
        raise NotImplementedError("unreachable")


def write_workunit(client: Bfabric, workunit_id: int, message: str) -> None:
    external_jobs = client.read(
        endpoint="externaljob",
        obj={
            "cliententityid": workunit_id,
            "cliententityclass": "Workunit",
            "action": "WORKUNIT",
        },
        return_id_only=True,
    )
    # TODO this sort of adds noise by creating "fetched by" messages to the log
    if len(external_jobs) != 1:
        raise ValueError(
            f"Expected exactly one external job for workunit {workunit_id}, but found {len(external_jobs)}"
        )
    else:
        write_externaljob(client=client, externaljob_id=external_jobs[0]["id"], message=message)


def write_externaljob(client: Bfabric, externaljob_id: int, message: str) -> None:
    pprint({"externaljob_id": externaljob_id, "message": message})
    client.save("externaljob", {"id": externaljob_id, "logthis": message})

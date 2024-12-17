from typing import Annotated

import cyclopts

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric.entities import ExternalJob

cmd = cyclopts.App(help="write log messages to workunits and external jobs")

log_target = cyclopts.Group(
    "Log Target",
    validator=cyclopts.validators.LimitedChoice(min=1),
)


@cmd.command
def write(
    message: str,
    *,
    workunit: Annotated[int, cyclopts.Parameter(group=log_target)] = None,
    externaljob: Annotated[int, cyclopts.Parameter(group=log_target)] = None,
) -> None:
    from rich.pretty import pprint

    pprint(locals())
    if workunit:
        write_workunit(workunit_id=workunit, message=message)
    else:
        write_externaljob(externaljob_id=externaljob, message=message)


def write_workunit(workunit_id: int, message: str) -> None:
    setup_script_logging()
    client = Bfabric.from_config()
    # TODO this sort of adds noise by creating "fetched by" messages to the log
    external_jobs = ExternalJob.find_by(
        {"cliententityid": workunit_id, "cliententityclass": "Workunit", "action": "WORKUNIT"}, client=client
    )
    if len(external_jobs) != 1:
        raise ValueError(
            f"Expected exactly one external job for workunit {workunit_id}, but found {len(external_jobs)}"
        )
    else:
        [external_job] = external_jobs.values()
        write_externaljob(externaljob_id=external_job.id, message=message)


def write_externaljob(externaljob_id: int, message: str) -> None:
    setup_script_logging()
    client = Bfabric.from_config()
    client.save("externaljob", {"id": externaljob_id, "logthis": message})

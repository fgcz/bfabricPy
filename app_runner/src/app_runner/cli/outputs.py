from __future__ import annotations


import cyclopts

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric.entities import Workunit
from app_runner.output_registration.spec import OutputsSpec
from app_runner.output_registration.register import register_all
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

app_outputs = cyclopts.App("outputs", help="Register output files for an app.")


@app_outputs.command()
def register(
    outputs_yaml: Path,
    # TODO we should use the workunit definition instead
    workunit_id: int,
    *,
    ssh_user: str | None = None,
    # TODO
    reuse_default_resource: bool = True,
) -> None:
    """Register the output files of a workunit."""
    setup_script_logging()
    client = Bfabric.from_config()

    specs_list = OutputsSpec.read_yaml(outputs_yaml)
    workunit = Workunit.find(id=workunit_id, client=client)
    register_all(
        client=client,
        workunit=workunit,
        specs_list=specs_list,
        ssh_user=ssh_user,
        reuse_default_resource=reuse_default_resource,
    )

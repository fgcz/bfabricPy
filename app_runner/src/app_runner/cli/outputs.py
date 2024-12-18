from __future__ import annotations

from pathlib import Path

import cyclopts

from app_runner.output_registration.register import register_all
from app_runner.specs.outputs_spec import OutputsSpec
from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric.experimental.workunit_definition import WorkunitDefinition

app_outputs = cyclopts.App("outputs", help="Register output files for an app.")


@app_outputs.command()
def register(
    outputs_yaml: Path,
    workunit_ref: int | Path,
    *,
    ssh_user: str | None = None,
    # TODO
    reuse_default_resource: bool = True,
) -> None:
    """Register the output files of a workunit."""
    setup_script_logging()
    client = Bfabric.from_config()
    workunit_ref = workunit_ref.resolve() if isinstance(workunit_ref, Path) else workunit_ref
    # TODO can we do better and provide a cache_file even here?
    workunit_definition = WorkunitDefinition.from_ref(workunit=workunit_ref, client=client, cache_file=None)
    specs_list = OutputsSpec.read_yaml(outputs_yaml)
    register_all(
        client=client,
        workunit_definition=workunit_definition,
        specs_list=specs_list,
        ssh_user=ssh_user,
        reuse_default_resource=reuse_default_resource,
    )

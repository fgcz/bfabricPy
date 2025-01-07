from __future__ import annotations

from pathlib import Path

import cyclopts
from rich.pretty import pprint

from app_runner.output_registration.register import register_all
from app_runner.specs.outputs_spec import OutputsSpec, CopyResourceSpec, UpdateExisting
from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric.entities import Workunit

app_outputs = cyclopts.App("outputs", help="Register output files for an app.")


def _get_workunit(client: Bfabric, workunit_id: int) -> Workunit:
    """Get the workunit with the given id and raises an error if it is not found."""
    workunit = Workunit.find(id=workunit_id, client=client)
    if workunit is None:
        msg = f"Workunit with id {workunit_id} not found"
        raise ValueError(msg)
    return workunit


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
    register_all(
        client=client,
        workunit=_get_workunit(client, workunit_id),
        specs_list=specs_list,
        ssh_user=ssh_user,
        reuse_default_resource=reuse_default_resource,
    )


@app_outputs.command()
def register_single_file(
    local_path: Path,
    *,
    workunit_id: int,
    store_entry_path: Path | None = None,
    store_folder_path: Path | None = None,
    update_existing: UpdateExisting = UpdateExisting.NO,
    ssh_user: str | None = None,
    reuse_default_resource: bool = False,
) -> None:
    """Register a single file in the workunit.

    In general, it is recommended to use the `register` command instead of this one and declare files using YAML.
    """
    setup_script_logging()
    client = Bfabric.from_config()

    if store_entry_path is None:
        store_entry_path = local_path.name

    spec = CopyResourceSpec(
        local_path=local_path,
        store_entry_path=store_entry_path,
        store_folder_path=store_folder_path,
        update_existing=update_existing,
    )
    pprint(spec)
    register_all(
        client=client,
        workunit=_get_workunit(client, workunit_id),
        specs_list=[spec],
        ssh_user=ssh_user,
        reuse_default_resource=reuse_default_resource,
    )

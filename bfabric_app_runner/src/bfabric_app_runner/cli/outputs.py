from __future__ import annotations

from pathlib import Path

import cyclopts
from rich.pretty import pprint

from bfabric_app_runner.output_registration.register import register_all
from bfabric_app_runner.specs.outputs_spec import OutputsSpec, CopyResourceSpec, UpdateExisting
from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric.experimental.workunit_definition import WorkunitDefinition

app_outputs = cyclopts.App("outputs", help="Register output files for an app.")


def _get_workunit_definition(client: Bfabric, workunit_ref: int | Path) -> WorkunitDefinition:
    """Get the workunit with the given id and raises an error if it is not found."""
    workunit_ref = workunit_ref.resolve() if isinstance(workunit_ref, Path) else workunit_ref
    # TODO can we do better and provide a cache_file even here?
    return WorkunitDefinition.from_ref(workunit=workunit_ref, client=client, cache_file=None)


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
    specs_list = OutputsSpec.read_yaml(outputs_yaml)
    register_all(
        client=client,
        workunit_definition=_get_workunit_definition(client, workunit_ref),
        specs_list=specs_list,
        ssh_user=ssh_user,
        reuse_default_resource=reuse_default_resource,
    )


@app_outputs.command()
def register_single_file(
    local_path: Path,
    *,
    workunit_ref: int | Path,
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
        workunit_definition=_get_workunit_definition(client, workunit_ref),
        specs_list=[spec],
        ssh_user=ssh_user,
        reuse_default_resource=reuse_default_resource,
    )

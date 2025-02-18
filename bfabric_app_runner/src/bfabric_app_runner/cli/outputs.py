from pathlib import Path

from rich.pretty import pprint

from bfabric import Bfabric
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.output_registration.register import register_all
from bfabric_app_runner.specs.outputs_spec import OutputsSpec, CopyResourceSpec, UpdateExisting


def _get_workunit_definition(client: Bfabric, workunit_ref: int | Path) -> WorkunitDefinition:
    """Get the workunit with the given id and raises an error if it is not found."""
    workunit_ref = workunit_ref.resolve() if isinstance(workunit_ref, Path) else workunit_ref
    # TODO can we do better and provide a cache_file even here?
    return WorkunitDefinition.from_ref(workunit=workunit_ref, client=client, cache_file=None)


@use_client
def cmd_outputs_register(
    outputs_yaml: Path,
    workunit_ref: int | Path,
    *,
    ssh_user: str | None = None,
    force_storage: Path | None = None,
    client: Bfabric,
    # TODO
    reuse_default_resource: bool = True,
) -> None:
    """Register the output files of a workunit."""
    specs_list = OutputsSpec.read_yaml(outputs_yaml)
    register_all(
        client=client,
        workunit_definition=_get_workunit_definition(client, workunit_ref),
        specs_list=specs_list,
        ssh_user=ssh_user,
        reuse_default_resource=reuse_default_resource,
        force_storage=force_storage,
    )


@use_client
def cmd_outputs_register_single_file(
    local_path: Path,
    *,
    workunit_ref: int | Path,
    store_entry_path: Path | None = None,
    store_folder_path: Path | None = None,
    update_existing: UpdateExisting = UpdateExisting.NO,
    ssh_user: str | None = None,
    force_storage: Path | None = None,
    reuse_default_resource: bool = False,
    client: Bfabric,
) -> None:
    """Register a single file in the workunit.

    In general, it is recommended to use the `register` command instead of this one and declare files using YAML.
    """
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
        force_storage=force_storage,
    )

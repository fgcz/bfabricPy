from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from bfabric_app_runner.specs.outputs_spec import (
    CopyResourceSpec,
    UpdateExisting,
    OutputsSpec,
    SpecType,
    SaveDatasetSpec,
)
from bfabric_app_runner.util.checksums import md5sum
from bfabric_app_runner.util.scp import scp
from bfabric.entities import Resource
from bfabric.entities import Storage, Workunit
from bfabric.experimental.upload_dataset import bfabric_save_csv2dataset

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric import Bfabric
    from bfabric.experimental.workunit_definition import WorkunitDefinition


def _get_output_folder(spec: CopyResourceSpec, workunit_definition: WorkunitDefinition) -> Path:
    if not spec.store_folder_path:
        return workunit_definition.registration.storage_output_folder
    else:
        return spec.store_folder_path


def register_file_in_workunit(
    spec: CopyResourceSpec,
    client: Bfabric,
    workunit_definition: WorkunitDefinition,
    resource_id: int | None = None,
) -> None:
    """Registers a file in the workunit."""
    existing_id = _identify_existing_resource_id(client, spec, workunit_definition)
    if resource_id is not None and existing_id is not None and resource_id != existing_id:
        raise ValueError(f"Resource id {resource_id} does not match existing resource id {existing_id}")

    checksum = md5sum(spec.local_path)
    output_folder = _get_output_folder(spec, workunit_definition=workunit_definition)
    resource_data = {
        "name": spec.store_entry_path.name,
        "workunitid": workunit_definition.registration.workunit_id,
        "storageid": workunit_definition.registration.storage_id,
        "relativepath": output_folder / spec.store_entry_path,
        "filechecksum": checksum,
        "status": "available",
        "size": spec.local_path.stat().st_size,
    }
    if resource_id is not None:
        resource_data["id"] = resource_id
    if existing_id is not None:
        resource_data["id"] = existing_id

    client.save("resource", resource_data)


def _identify_existing_resource_id(
    client: Bfabric, spec: CopyResourceSpec, workunit_definition: WorkunitDefinition
) -> int | None:
    """Returns the id of the existing resource if it exists."""
    if spec.update_existing in (UpdateExisting.IF_EXISTS, UpdateExisting.REQUIRED):
        # TODO maybe it would be more accurate to use relativepath here, however historically it would often start
        #      with `/` which can be confusing.
        resources = Resource.find_by(
            {
                "name": spec.store_entry_path.name,
                "workunitid": workunit_definition.registration.workunit_id,
            },
            client=client,
        ).values()
        if resources:
            return list(resources)[0].id
        elif spec.update_existing == UpdateExisting.REQUIRED:
            raise ValueError(f"Resource {spec.store_entry_path.name} not found in workunit {workunit_definition.id}")
    return None


def copy_file_to_storage(
    spec: CopyResourceSpec,
    workunit_definition: WorkunitDefinition,
    storage: Storage,
    ssh_user: str | None,
) -> None:
    """Copies a file to the storage, according to the spec."""
    # TODO here some direct uses of storage could still be optimized away
    output_folder = _get_output_folder(spec, workunit_definition=workunit_definition)
    output_uri = f"{storage.scp_prefix}{output_folder / spec.store_entry_path}"
    scp(spec.local_path, output_uri, user=ssh_user)


def _save_dataset(spec: SaveDatasetSpec, client: Bfabric, workunit_definition: WorkunitDefinition) -> None:
    """Saves a dataset to the bfabric."""
    # TODO should not print to stdout in the future
    # TODO also it should not be imported from bfabric_scripts, but rather the generic functionality should be available
    #      in the main package
    bfabric_save_csv2dataset(
        client=client,
        csv_file=spec.local_path,
        dataset_name=spec.name or spec.local_path.stem,
        container_id=workunit_definition.registration.container_id,
        workunit_id=workunit_definition.registration.workunit_id,
        sep=spec.separator,
        has_header=spec.has_header,
        invalid_characters=spec.invalid_characters,
    )


def find_default_resource_id(workunit_definition: WorkunitDefinition, client: Bfabric) -> int | None:
    """Finds the default resource's id for the workunit. Maybe in the future, this will be always `None`."""
    workunit = Workunit.find(id=workunit_definition.registration.workunit_id, client=client)
    candidate_resources = [
        resource for resource in workunit.resources if resource["name"] not in ["slurm_stdout", "slurm_stderr"]
    ]
    # We also check that the resource is pending, as else we might re-use a resource that was created by the app...
    if len(candidate_resources) == 1 and candidate_resources[0]["status"] == "pending":
        return candidate_resources[0].id
    return None


def register_all(
    client: Bfabric,
    workunit_definition: WorkunitDefinition,
    specs_list: list[SpecType],
    ssh_user: str | None,
    reuse_default_resource: bool,
) -> None:
    """Registers all the output specs to the workunit."""
    default_resource_was_reused = not reuse_default_resource
    for spec in specs_list:
        logger.debug(f"Registering {spec}")
        if isinstance(spec, CopyResourceSpec):
            storage = Storage.find(workunit_definition.registration.storage_id, client=client)
            copy_file_to_storage(
                spec,
                workunit_definition=workunit_definition,
                storage=storage,
                ssh_user=ssh_user,
            )
            if not default_resource_was_reused:
                resource_id = find_default_resource_id(workunit_definition=workunit_definition, client=client)
                default_resource_was_reused = True
            else:
                resource_id = None
            register_file_in_workunit(
                spec,
                client=client,
                workunit_definition=workunit_definition,
                resource_id=resource_id,
            )
        elif isinstance(spec, SaveDatasetSpec):
            _save_dataset(spec, client, workunit_definition=workunit_definition)
        else:
            raise ValueError(f"Unknown spec type: {type(spec)}")


def register_outputs(
    outputs_yaml: Path,
    workunit_definition: WorkunitDefinition,
    client: Bfabric,
    ssh_user: str | None,
    reuse_default_resource: bool,
) -> None:
    """Registers outputs to the workunit."""
    specs_list = OutputsSpec.read_yaml(outputs_yaml)
    register_all(
        client=client,
        workunit_definition=workunit_definition,
        specs_list=specs_list,
        ssh_user=ssh_user,
        reuse_default_resource=reuse_default_resource,
    )

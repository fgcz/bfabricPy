from __future__ import annotations

from pathlib import Path

from loguru import logger

from bfabric import Bfabric
from bfabric.entities import Storage, Workunit
from app_runner.output_registration.spec import (
    CopyResourceSpec,
    UpdateExisting,
    OutputsSpec,
    SpecType,
    SaveDatasetSpec,
)
from app_runner.util.checksums import md5sum
from app_runner.util.scp import scp
from bfabric_scripts.bfabric_save_csv2dataset import bfabric_save_csv2dataset


def _get_output_folder(spec: CopyResourceSpec, workunit: Workunit) -> Path:
    if not spec.store_folder_path:
        return workunit.store_output_folder
    else:
        return spec.store_folder_path


def register_file_in_workunit(
    spec: CopyResourceSpec,
    client: Bfabric,
    workunit: Workunit,
    storage: Storage,
    resource_id: int | None = None,
):
    if spec.update_existing != UpdateExisting.NO:
        # TODO implement this functionality
        raise NotImplementedError("Update existing not implemented")
    checksum = md5sum(spec.local_path)
    output_folder = _get_output_folder(spec, workunit=workunit)
    resource_data = {
        "name": spec.store_entry_path.name,
        "workunitid": workunit.id,
        "storageid": storage.id,
        "relativepath": output_folder / spec.store_entry_path,
        "filechecksum": checksum,
        "status": "available",
        "size": spec.local_path.stat().st_size,
    }
    if resource_id is not None:
        resource_data["id"] = resource_id
    client.save("resource", resource_data)


def copy_file_to_storage(spec: CopyResourceSpec, workunit: Workunit, storage: Storage, ssh_user: str | None):
    output_folder = _get_output_folder(spec, workunit=workunit)
    output_uri = f"{storage.scp_prefix}{output_folder / spec.store_entry_path}"
    scp(spec.local_path, output_uri, user=ssh_user)


def _save_dataset(spec: SaveDatasetSpec, client: Bfabric, workunit: Workunit):
    # TODO should not print to stdout in the future
    # TODO also it should not be imported from bfabric_scripts, but rather the generic functioanlity should be available
    #      in the main package
    bfabric_save_csv2dataset(
        client=client,
        csv_file=spec.local_path,
        dataset_name=spec.name or spec.local_path.stem,
        container_id=workunit.container.id,
        workunit_id=workunit.id,
        sep=spec.separator,
        has_header=spec.has_header,
        invalid_characters=spec.invalid_characters,
    )


def find_default_resource_id(workunit: Workunit) -> int | None:
    candidate_resources = [
        resource for resource in workunit.resources if resource["name"] not in ["slurm_stdout", "slurm_stderr"]
    ]
    # We also check that the resource is pending, as else we might re-use a resource that was created by the app...
    if len(candidate_resources) == 1 and candidate_resources[0]["status"] == "pending":
        return candidate_resources[0].id
    return None


def register_all(
    client: Bfabric, workunit: Workunit, specs_list: list[SpecType], ssh_user: str | None, reuse_default_resource: bool
):
    default_resource_was_reused = not reuse_default_resource
    for spec in specs_list:
        logger.debug(f"Registering {spec}")
        if isinstance(spec, CopyResourceSpec):
            storage = workunit.application.storage
            copy_file_to_storage(spec, workunit=workunit, storage=storage, ssh_user=ssh_user)
            if not default_resource_was_reused:
                resource_id = find_default_resource_id(workunit=workunit)
                default_resource_was_reused = True
            else:
                resource_id = None
            register_file_in_workunit(spec, client=client, workunit=workunit, storage=storage, resource_id=resource_id)
        elif isinstance(spec, SaveDatasetSpec):
            _save_dataset(spec, client, workunit=workunit)
        else:
            raise ValueError(f"Unknown spec type: {type(spec)}")


def register_outputs(
    outputs_yaml: Path,
    workunit_id: int,
    client: Bfabric,
    ssh_user: str | None,
    reuse_default_resource: bool,
) -> None:
    # parse the specs
    specs_list = OutputsSpec.read_yaml(outputs_yaml)

    # register all specs
    workunit = Workunit.find(id=workunit_id, client=client)
    register_all(
        client=client,
        workunit=workunit,
        specs_list=specs_list,
        ssh_user=ssh_user,
        reuse_default_resource=reuse_default_resource,
    )

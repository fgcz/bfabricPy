from __future__ import annotations

from pathlib import Path

from loguru import logger

from bfabric import Bfabric
from bfabric.entities import Storage, Workunit
from bfabric.experimental.app_interface.output_registration._spec import (
    CopyResourceSpec,
    UpdateExisting,
    OutputsSpec,
    SpecType,
    SaveDatasetSpec,
)
from bfabric.experimental.app_interface.util.checksums import md5sum
from bfabric.experimental.app_interface.util.scp import scp
from bfabric.scripts.bfabric_save_csv2dataset import bfabric_save_csv2dataset


def _get_output_folder(spec: CopyResourceSpec, client: Bfabric) -> Path:
    if not spec.store_folder_path:
        return Workunit.find(id=spec.workunit_id, client=client).store_output_folder
    else:
        return spec.store_folder_path


def register_file_in_workunit(
    spec: CopyResourceSpec,
    client: Bfabric,
):
    if spec.update_existing != UpdateExisting.NO:
        # TODO implement this functionality
        raise NotImplementedError("Update existing not implemented")
    checksum = md5sum(spec.local_path)
    output_folder = _get_output_folder(spec, client)
    client.save(
        "resource",
        {
            "name": spec.store_entry_path.name,
            "workunitid": spec.workunit_id,
            "storageid": spec.storage_id,
            "relativepath": output_folder / spec.store_entry_path,
            "filechecksum": checksum,
            "status": "available",
            "size": spec.local_path.stat().st_size,
        },
    )


def copy_file_to_storage(spec: CopyResourceSpec, client: Bfabric, ssh_user: str | None):
    storage = Storage.find(id=spec.storage_id, client=client)
    output_folder = _get_output_folder(spec, client)
    output_uri = f"{storage.scp_prefix}{output_folder / spec.store_entry_path}"
    scp(spec.local_path, output_uri, user=ssh_user)


def _save_dataset(spec: SaveDatasetSpec, client: Bfabric):
    # TODO should not print to stdout in the future
    workunit = Workunit.find(id=spec.workunit_id, client=client)
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


def register_all(client: Bfabric, specs_list: list[SpecType], ssh_user: str | None):
    for spec in specs_list:
        logger.debug(f"Registering {spec}")
        if isinstance(spec, CopyResourceSpec):
            copy_file_to_storage(spec, client, ssh_user)
            register_file_in_workunit(spec, client)
        elif isinstance(spec, SaveDatasetSpec):
            _save_dataset(spec, client)
        else:
            raise ValueError(f"Unknown spec type: {type(spec)}")


def register_outputs(
    outputs_yaml: Path,
    client: Bfabric,
    # local_folder: Path | None,
    ssh_user: str | None,
) -> None:
    # if local_folder is None:
    #    # TODO this is consistent with prepare, but maybe unexpected?
    #    local_folder = outputs_yaml.parent
    # TODO local folder is not used!

    # parse the specs
    specs_list = OutputsSpec.read_yaml(outputs_yaml)

    # process each spec
    register_all(client=client, specs_list=specs_list, ssh_user=ssh_user)

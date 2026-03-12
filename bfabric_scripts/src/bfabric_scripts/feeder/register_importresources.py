from __future__ import annotations

from enum import StrEnum
import os
import time

from loguru import logger

from bfabric import Bfabric, BfabricClientConfig
from bfabric_scripts.feeder.file_attributes import get_file_attributes
from pydantic import BaseModel


class RegistrationStatus(StrEnum):
    registered = "registered"
    pending = "pending"
    failed_unknown_error = "failed_unknown_error"
    failed_deterministic = "failed_deterministic"
    failed_unknown_application = "failed_unknown_application"


class FeederConfig(BaseModel):
    storage_id: int


class ApplicationLookup(BaseModel):
    pass


def create_importresource_dict(
    # config: BfabricClientConfig,
    feeder_config: FeederConfig,
    file_path: str,
    file_size: int,
    file_unix_timestamp: int,
    md5_checksum,
) -> dict[str, str | int]:
    # Format the timestamp for bfabric
    file_date = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(file_unix_timestamp))
    bfabric_application_ids = config.application_ids
    if not bfabric_application_ids:
        raise RuntimeError("No bfabric_application_ids configured. check '~/.bfabricpy.yml' file!")
    bfabric_application_id, bfabric_projectid = get_bfabric_application_and_project_id(
        bfabric_application_ids, file_path
    )
    obj = {
        "applicationid": bfabric_application_id,
        "filechecksum": md5_checksum,
        "containerid": bfabric_projectid,
        "filedate": file_date,
        "relativepath": file_path,
        "name": os.path.basename(file_path),
        "size": file_size,
        "storageid": feeder_config.storage_id,
    }
    sample_id = get_sample_id_from_path(file_path)
    if sample_id is not None:
        obj["sampleid"] = sample_id
    return obj

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from bfabric_app_runner.specs.common_types import RelativeFilePath


class BfabricResourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_resource"] = "bfabric_resource"

    id: int
    """B-Fabric resource ID"""

    filename: RelativeFilePath | None = None
    """Target filename to save to"""

    check_checksum: bool = True
    """Whether to check the checksum of the file, after downloading"""

    access: Literal["ssh", "http"] = "ssh"
    """Transport used to fetch the file.

    ``ssh`` copies it from the storage host over rsync/scp and requires SSH/NFS access. ``http``
    streams it from the storage's HTTP access endpoint; portable (works anywhere with web access)
    but slower, and requires an OAuth-backed client to provide a bearer token.
    """

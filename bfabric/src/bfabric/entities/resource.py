from __future__ import annotations

from pathlib import Path
from typing import Any, TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities.storage import Storage
    from bfabric.entities.workunit import Workunit
    from bfabric.entities import Sample


class Resource(Entity):
    ENDPOINT = "resource"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None = None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    storage: HasOne[Storage] = HasOne("Storage", bfabric_field="storage")
    workunit: HasOne[Workunit] = HasOne("Workunit", bfabric_field="workunit")
    sample: HasOne[Sample] = HasOne("Sample", bfabric_field="sample", optional=True)

    @property
    def storage_relative_path(self) -> Path:
        """Returns the relative path of the resource in the storage as a Path object."""
        return Path(self["relativepath"].lstrip("/"))

    @property
    def storage_absolute_path(self) -> Path:
        """Returns the absolute path of the resource in the storage as a Path object."""
        return Path(self.storage.base_path) / self.storage_relative_path

    @property
    def filename(self) -> str:
        """Returns the filename of the actual path, i.e. not necessarily the resource name but rather the name
        as the file is stored.
        """
        return self["relativepath"].split("/")[-1]

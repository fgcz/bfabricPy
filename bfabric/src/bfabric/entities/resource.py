from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne

if TYPE_CHECKING:
    from bfabric.entities import Sample
    from bfabric.entities.storage import Storage
    from bfabric.entities.workunit import Workunit


class Resource(Entity):
    ENDPOINT = "resource"

    storage: HasOne[Storage] = HasOne(bfabric_field="storage")
    workunit: HasOne[Workunit] = HasOne(bfabric_field="workunit")
    sample: HasOne[Sample] = HasOne(bfabric_field="sample", optional=True)

    @property
    def storage_relative_path(self) -> Path:
        """Returns the relative path of the resource in the storage as a Path object."""
        relative_path = self["relativepath"]
        if not isinstance(relative_path, str):
            raise ValueError("relativepath value must be a string")
        return Path(relative_path.lstrip("/"))

    @property
    def storage_absolute_path(self) -> Path:
        """Returns the absolute path of the resource in the storage as a Path object."""
        return Path(self.storage.base_path) / self.storage_relative_path

    @property
    def filename(self) -> str:
        """Returns the filename of the actual path, i.e. not necessarily the resource name but rather the name
        as the file is stored.
        """
        return self.storage_relative_path.name

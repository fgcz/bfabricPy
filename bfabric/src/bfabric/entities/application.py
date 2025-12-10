from __future__ import annotations

from typing import TYPE_CHECKING, TypeGuard

from pydantic import TypeAdapter

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne
from bfabric.utils.path_safe_name import PathSafeStr

if TYPE_CHECKING:
    from bfabric.engine.types import ApiResponseDataType
    from bfabric.entities.executable import Executable
    from bfabric.entities.storage import Storage


class Application(Entity):
    ENDPOINT = "application"

    storage: HasOne[Storage] = HasOne(bfabric_field="storage")
    executable: HasOne[Executable] = HasOne(bfabric_field="executable")

    @property
    def technology_folder_name(self) -> PathSafeStr:
        """Returns the technology which is used e.g. for output registration."""
        technology = self.data_dict["technology"]
        if not _is_technology_list(technology):
            raise ValueError("Technology must be a list of strings")
        technology = sorted(technology)[0]
        return TypeAdapter(PathSafeStr).validate_python(technology)


def _is_technology_list(technology: ApiResponseDataType) -> TypeGuard[list[str]]:
    if not isinstance(technology, list):
        return False
    return all(isinstance(t, str) for t in technology)

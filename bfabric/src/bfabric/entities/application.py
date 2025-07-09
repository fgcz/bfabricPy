from __future__ import annotations

from typing import Any, TYPE_CHECKING

from pydantic import TypeAdapter

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne
from bfabric.utils.path_safe_name import PathSafeStr

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities.executable import Executable
    from bfabric.entities.storage import Storage


class Application(Entity):
    ENDPOINT = "application"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    storage: HasOne[Storage] = HasOne("Storage", bfabric_field="storage")
    executable: HasOne[Executable] = HasOne("Executable", bfabric_field="executable")

    @property
    def technology_folder_name(self) -> PathSafeStr:
        """Returns the technology which is used e.g. for output registration."""
        technology = self.data_dict["technology"]
        if isinstance(technology, list):
            # TODO certainly this can be improved, also in the future it may always be a list (right now it is not
            #      rolled out yet)
            technology = sorted(technology)[0]
        return TypeAdapter(PathSafeStr).validate_python(technology)

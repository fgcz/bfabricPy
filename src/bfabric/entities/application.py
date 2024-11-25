from __future__ import annotations

from typing import Any, TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne

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

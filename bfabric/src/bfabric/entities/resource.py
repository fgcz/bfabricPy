from __future__ import annotations

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

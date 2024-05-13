from __future__ import annotations

from typing import Any

from bfabric import Bfabric


class DeleteEntities:
    """Deletes entities that were registered, when a test is torn down.
    Please use `self.addCleanup` to ensure that the entities are deleted even if the test fails.
    """

    def __init__(self, client: Bfabric, created_entities: list[tuple[str, int]] | None = None) -> None:
        self.client = client
        self.created_entities = created_entities or []

    def __call__(self) -> None:
        """Deletes all created entities."""
        errors = []
        for entity_type, entity_id in self.created_entities:
            errors += self.client.delete(entity_type, entity_id, check=False).errors
        if errors:
            print("Error deleting entities:", errors)
        else:
            print("Successfully deleted entities:", self.created_entities)

    def register_entity(self, entity: dict[str, Any], entity_type: str | None = None) -> None:
        """Registers an entity to be deleted when the test is torn down."""
        if entity_type is None:
            entity_type = entity["classname"]
        self.created_entities.append((entity_type, entity["id"]))

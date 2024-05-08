from __future__ import annotations

from bfabric.bfabric2 import Bfabric


class DeleteEntities:
    def __init__(self, client: Bfabric, created_entities: list[tuple[str, int]]):
        self.client = client
        self.created_entities = created_entities

    def __call__(self):
        errors = []
        for entity_type, entity_id in self.created_entities:
            errors += self.client.delete(entity_type, entity_id, check=False).errors
        if errors:
            print("Error deleting entities:", errors)
        else:
            print("Successfully deleted entities:", self.created_entities)
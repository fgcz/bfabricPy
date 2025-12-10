from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric.entities.core.uri import EntityUri

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.results.result_container import ResultContainer


def update_custom_attributes(
    client: Bfabric, entity_uri: EntityUri | str, custom_attributes: dict[str, str], *, replace: bool = False
) -> ResultContainer:
    """Updates the custom attributes of the specified entity.

    NOTE: Use in cache contexts may lead to unwanted consequences, if custom attributes are updated by a different
    application.

    :param client: Bfabric client
    :param entity_uri: Entity URI
    :param custom_attributes: Custom attributes to update
    :param replace: Replace existing custom attributes mapping, or update/add only the specified ones.
    """
    entity_uri = EntityUri(entity_uri)

    # read the current custom attributes (if requested)
    if replace:
        attributes_dict = {}
    else:
        entity = client.reader.read_uri(entity_uri)
        attributes_dict = entity.custom_attributes
    # merge new args
    attributes_dict.update(custom_attributes)
    # write the result
    attributes_list = [{"name": key, "value": value} for key, value in attributes_dict.items()]
    return client.save(
        entity_uri.components.entity_type, {"id": entity_uri.components.entity_id, "customattribute": attributes_list}
    )

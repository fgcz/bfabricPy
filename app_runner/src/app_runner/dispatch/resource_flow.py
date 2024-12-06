from loguru import logger

from bfabric import Bfabric
from bfabric.entities import Resource
from bfabric.experimental.workunit_definition import WorkunitDefinition


def get_resource_flow_input_resources(
    client: Bfabric,
    definition: WorkunitDefinition,
    filter_suffix: str | None,
) -> list[Resource]:
    """Returns the input resources for a resource flow workunit, applying e.g. a filter suffix."""
    all_resources = Resource.find_all(ids=definition.execution.resources, client=client)
    result_resources = []
    for resource in sorted(all_resources.values()):
        if filter_suffix is not None and not resource["relativepath"].endswith(filter_suffix):
            logger.info(f"Skipping resource {resource['relativepath']!r} as it does not match the extension filter.")
            continue
        result_resources.append(resource)
    return result_resources

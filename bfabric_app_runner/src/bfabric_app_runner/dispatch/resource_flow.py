from bfabric import Bfabric
from bfabric.entities import Resource
from bfabric.experimental.workunit_definition import WorkunitDefinition
from loguru import logger


def get_resource_flow_input_resources(
    client: Bfabric,
    definition: WorkunitDefinition,
    filter_suffix: str | None,
) -> list[Resource]:
    """Returns the input resources for a resource flow workunit, applying e.g. a filter suffix."""
    all_resources = client.reader.read_ids("resource", definition.execution.resources, expected_type=Resource)
    result_resources: list[Resource] = []
    for resource_uri, resource in all_resources.items():
        if resource is None:
            raise ValueError(f"Resource not found: {resource_uri}")
        if filter_suffix is not None and not resource.filename.endswith(filter_suffix):
            logger.info(f"Skipping resource {resource['relativepath']!r} as it does not match the extension filter.")
            continue
        result_resources.append(resource)
    return result_resources

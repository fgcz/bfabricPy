from loguru import logger
from rich.pretty import pprint

from bfabric import Bfabric
from bfabric.entities import Resource
from bfabric.results.result_container import ResultContainer
from bfabric_scripts.feeder.file_attributes import get_file_attributes


def report_resource(client: Bfabric, resource_id: int) -> ResultContainer:
    """Saves the provided resource's checksum, file size and available state."""
    resource = client.reader.read_id("resource", resource_id, expected_type=Resource)
    if resource is None:
        raise ValueError(f"Resource with ID {resource_id} not found")

    pprint(resource, indent_guides=False)

    if resource.storage is None:
        # TODO is this possible for a resource to not have a storage?
        logger.error("Resource does not have a storage")
        # TODO add the error?
        return ResultContainer([], total_pages_api=None, errors=[])

    filename = resource.storage_absolute_path
    logger.info("Testing file: {}", filename)
    if filename.is_file():
        # TODO determine future of this script before merging
        checksum, _, filesize, _ = get_file_attributes(str(filename))
        return client.save(
            "resource",
            {
                "id": resource_id,
                "size": filesize,
                "status": "available",
                "filechecksum": checksum,
            },
        )
    else:
        return client.save("resource", {"id": resource_id, "status": "failed"})

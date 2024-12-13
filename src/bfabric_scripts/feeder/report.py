from pathlib import Path

from loguru import logger
from rich.pretty import pprint

from bfabric import Bfabric
from bfabric.entities import Resource
from bfabric.results.result_container import ResultContainer
from bfabric_scripts.feeder.file_attributes import get_file_attributes


def report_resource(client: Bfabric, resource_id: int) -> ResultContainer:
    """Saves the provided resource's checksum, file size and available state."""
    resource = Resource.find(id=resource_id, client=client)
    pprint(resource, indent_guides=False)

    if not hasattr(resource, "storage"):
        # TODO is this possible for a resource to not have a storage?
        logger.error("Resource does not have a storage")
        return ResultContainer([])

    filename = Path(resource.storage["basepath"]) / resource["relativepath"]
    if filename.is_file():
        checksum, _, filesize, _ = get_file_attributes(str(filename))
        return client.save(
            "resource", {"id": resource_id, "size": filesize, "status": "available", "filechecksum": checksum}
        )
    else:
        return client.save("resource", {"id": resource_id, "status": "failed"})

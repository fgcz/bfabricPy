from pathlib import Path

from loguru import logger
from rich.pretty import pprint

from bfabric import Bfabric
from bfabric.entities import Resource
from bfabric.results.result_container import ResultContainer
from bfabric_scripts.feeder.file_attributes import get_file_attributes


def _make_relative(path: str) -> str:
    # TODO this is a hack which is necessary due to behavior of the legacy wrapper_creator, hopefully no
    #      other code uses leading slashes to indicate relative paths but this will be seen later when refactoring this
    #      away.
    # replaces any number of leading slashes with an empty string
    return path.lstrip("/")


def report_resource(client: Bfabric, resource_id: int) -> ResultContainer:
    """Saves the provided resource's checksum, file size and available state."""
    resource = Resource.find(id=resource_id, client=client)
    pprint(resource, indent_guides=False)

    if resource.storage is None:
        # TODO is this possible for a resource to not have a storage?
        logger.error("Resource does not have a storage")
        # TODO add the error?
        return ResultContainer([], total_pages_api=None, errors=[])

    relative_path = _make_relative(resource["relativepath"])
    filename = Path(resource.storage["basepath"]) / relative_path
    logger.info("Testing file: {}", filename)
    if filename.is_file():
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

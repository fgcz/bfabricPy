from bfabric.typing import ApiResponseDataType, ApiResponseObjectType
from rich.console import Console
from rich.panel import Panel
from rich.pretty import pprint

from bfabric import Bfabric
from bfabric.entities import Executable, Storage
from bfabric.utils.cli_integration import use_client


def get_storage_info(storage_id: int | None, client: Bfabric) -> ApiResponseDataType | None:
    if storage_id is None:
        return None
    storage = client.reader.read_id("storage", storage_id, expected_type=Storage)
    if storage is None:
        return None
    return {"id": storage.id, "name": storage["name"], "description": storage["description"]}


@use_client
def cmd_executable_show(executable_id: int, *, client: Bfabric) -> None:
    """Show metadata and encoded program for an executable."""
    console = Console()
    executable = client.reader.read_id("executable", executable_id, expected_type=Executable)
    if executable is None:
        raise ValueError(f"executable with id {executable_id} not found")
    metadata: ApiResponseObjectType = {
        key: executable.get(key) for key in ("id", "name", "description", "relativepath", "context", "program")
    }
    metadata["storage"] = get_storage_info(executable.storage.id if executable.storage else None, client)

    console.print(Panel("Executable Metadata"))
    pprint(metadata)

    console.print(Panel("Encoded Program"))
    if executable.decoded:
        console.print(executable.decoded)
    else:
        console.print("No encoded program found.")

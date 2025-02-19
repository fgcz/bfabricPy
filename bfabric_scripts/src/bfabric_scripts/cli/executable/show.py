from rich.console import Console
from rich.panel import Panel
from rich.pretty import pprint

from bfabric import Bfabric
from bfabric.entities import Executable, Storage
from bfabric.utils.cli_integration import use_client


def get_storage_info(storage_id: int | None, client: Bfabric) -> dict[str, str | int] | None:
    if storage_id is None:
        return None
    storage_info = Storage.find(storage_id, client=client)
    return {key: storage_info[key] for key in ("id", "name", "description")}


@use_client
def cmd_executable_show(executable_id: int, *, client: Bfabric) -> None:
    """Show metadata and encoded program for an executable."""
    console = Console()
    executable = Executable.find(executable_id, client=client)
    metadata = {key: executable.get(key) for key in ("id", "name", "description", "relativepath", "context", "program")}
    metadata["storage"] = get_storage_info(executable.storage.id if executable.storage else None, client)

    console.print(Panel("Executable Metadata"))
    pprint(metadata)

    console.print(Panel("Encoded Program"))
    if executable.decoded:
        console.print(executable.decoded)
    else:
        console.print("No encoded program found.")

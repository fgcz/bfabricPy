from pathlib import Path
from typing import Literal

import xmltodict
import yaml

from bfabric import Bfabric
from bfabric.entities import Executable
from bfabric.utils.cli_integration import use_client


@use_client
def cmd_executable_dump(
    executable_id: int, path: Path, *, format: Literal["xml", "yaml"] | None = None, client: Bfabric
) -> None:
    """Dumps an executable to a file in XML or YAML format."""
    if format is None:
        if path.suffix == ".xml":
            format = "xml"
        elif path.suffix in [".yml", ".yaml"]:
            format = "yaml"
        else:
            raise ValueError(f"Unknown file extension: {path.suffix}. Please specify --format.")

    results = Executable.find_by({"id": executable_id, "fulldetails": "true"}, client=client)
    if not results:
        raise ValueError(f"Executable with ID {executable_id} not found.")
    executable = list(results.values())[0]
    data = executable.data_dict
    data["parameter"] = [p.data_dict for p in executable.parameters.list]

    if format == "xml":
        path.write_text(xmltodict.unparse({"executable": data}, pretty=True))
    elif format == "yaml":
        path.write_text(yaml.safe_dump(data, sort_keys=False))

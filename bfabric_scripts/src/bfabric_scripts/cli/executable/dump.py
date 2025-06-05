import copy
from pathlib import Path
from typing import Literal, Any

import xmltodict
import yaml

from bfabric import Bfabric
from bfabric.entities import Executable
from bfabric.utils.cli_integration import use_client


def _delete_keys(data: Any, keys: set[str]) -> Any:
    if isinstance(data, list):
        return [_delete_keys(item, keys) for item in data]
    elif isinstance(data, dict):
        return {k: _delete_keys(v, keys) for k, v in data.items() if k not in keys}
    else:
        return data


def _clean(executable_data: dict[str, Any]) -> dict[str, Any]:
    """Cleans the executable data so it can be uploaded again through the webservice api, removing some fields that give errors otherwise."""
    executable_data = copy.deepcopy(executable_data)
    del executable_data["id"]
    executable_data = _delete_keys(
        executable_data,
        {
            "created",
            "createdby",
            "modified",
            "modifiedby",
            "statusmodified",
            "statusmodifiedby",
            "supervisor",
            "classname",
            "filechecksum",
            "size",
            "inUse",
            "parentAllowsModification",
        },
    )
    for parameter in executable_data["parameter"]:
        parameter.pop("executable", None)
    return executable_data


@use_client
def cmd_executable_dump(
    executable_id: int,
    path: Path,
    *,
    format: Literal["xml", "yaml"] | None = None,
    clean: bool = True,
    client: Bfabric,
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
    if clean:
        data = _clean(data)
    result = {"executable": data}

    if format == "xml":
        path.write_text(xmltodict.unparse(result, pretty=True))
    elif format == "yaml":
        path.write_text(yaml.safe_dump(result, sort_keys=False))

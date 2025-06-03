import base64
from pathlib import Path
from typing import Literal, Any

import xmltodict
import yaml
from rich.console import Console

from bfabric import Bfabric
from bfabric.entities import Executable
from bfabric.utils.cli_integration import use_client


@use_client
def cmd_executable_upload(
    metadata_file: Path,
    *,
    client: Bfabric,
    upload: Path | None = None,
    metadata_file_format: Literal["xml", "yaml"] | None = None,
) -> None:
    """Uploads an executable defined in the specified YAML or XML to bfabric.

    :param metadata_file: Path to the YAML or XML file containing the executable metadata.
    :param upload: Path to the executable file to upload through the API, if no program is specified in the YAML instead
    :param metadata_file_format: Explicit format of the executable metadata file
    """
    # Determine input file format
    if metadata_file_format is None:
        if metadata_file.suffix in (".yaml", ".yml"):
            metadata_file_format = "yaml"
        elif metadata_file.suffix == ".xml":
            metadata_file_format = "xml"
        else:
            msg = f"Unknown file extension {metadata_file.suffix}, please specify the format explicitly."
            raise ValueError(msg)

    # Collect the input
    executable_data = read_executable_data(metadata_file=metadata_file, metadata_file_format=metadata_file_format)
    if "executable" not in executable_data:
        msg = "Metadata file must contain an 'executable' key."
        raise ValueError(msg)
    if len(executable_data) != 1:
        msg = "Metadata file must contain only the 'executable' key."
        raise ValueError(msg)
    executable_data = executable_data["executable"]
    if upload is not None:
        executable_data["base64"] = base64.encodebytes(upload.read_bytes()).decode("utf-8")

    # Ensure id is not set
    if "id" in executable_data:
        msg = "Executable data must not contain an 'id' key."
        raise ValueError(msg)

    console = Console()
    console.print_json(data=executable_data)

    # Perform the request
    result = client.save("executable", executable_data)
    executable_id = result[0]["id"]

    console.print("Executable uploaded successfully.")
    console.print("Executable ID:", executable_id)
    console.print("Executable URL:", Executable({"id": executable_id}, client=client).web_url)


def read_executable_data(metadata_file: Path, metadata_file_format: Literal["xml", "yaml"]) -> dict[str, Any]:
    """Reads the executable metadata from a YAML or XML file."""
    if metadata_file_format == "yaml":
        return yaml.safe_load(metadata_file.read_text())
    elif metadata_file_format == "xml":
        return xmltodict.parse(metadata_file.read_text())
    else:
        raise ValueError(f"Should be unreachable: {metadata_file_format}")
        # Py 3.11
        # assert_never(metadata_file_format)

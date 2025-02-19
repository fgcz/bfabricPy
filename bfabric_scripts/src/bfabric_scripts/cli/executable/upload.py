import base64
from pathlib import Path

import yaml
from rich.console import Console

from bfabric import Bfabric
from bfabric.entities import Executable
from bfabric.utils.cli_integration import use_client


@use_client
def cmd_executable_upload(executable_yaml: Path, *, upload: Path | None = None, client: Bfabric) -> None:
    """Uploads an executable defined in the specified YAML to bfabric.

    :param executable_yaml: Path to the YAML file containing the executable data.
    :param upload: Path to the executable file to upload through the API, if no program is specified in the YAML instead
    """
    # Collect the input
    executable_data = yaml.safe_load(executable_yaml.read_text())
    if "executable" not in executable_data:
        msg = "Yaml must contain an 'executable' key."
        raise ValueError(msg)
    if len(executable_data) != 1:
        msg = "Yaml must contain only the 'executable' key."
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

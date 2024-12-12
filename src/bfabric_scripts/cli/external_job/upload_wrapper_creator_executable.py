import base64
from pathlib import Path

from rich.pretty import pprint

from bfabric import Bfabric


def upload_wrapper_creator_executable_impl(client: Bfabric, filename: Path):
    executable_content = filename.read_text()
    attr = {
        "name": "yaml 004",
        "context": "WRAPPERCREATOR",
        "parameter": None,
        "description": "None.",
        "masterexecutableid": 11851,
        "base64": base64.b64encode(executable_content),
    }
    result = client.save("executable", attr)
    pprint(result)
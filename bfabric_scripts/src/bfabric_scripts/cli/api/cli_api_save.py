import cyclopts
from loguru import logger
from rich.pretty import pprint

from bfabric import Bfabric
from bfabric_scripts.cli.base import use_client

app = cyclopts.App()


@app.default
@use_client
def bfabric_save(
    endpoint: str,
    entity_id: int,
    attributes: list[tuple[str, str]] | None = None,
    *,
    client: Bfabric,
) -> None:
    if attributes is None:
        logger.warning("No attributes provided, doing nothing.")
        return
    attributes_dict = {attribute: value for attribute, value in attributes}
    if "id" in attributes_dict:
        logger.warning("Attribute 'id' is not allowed in the attributes, removing it.")
        del attributes
    result = client.save(endpoint, {"id": entity_id, **attributes_dict})
    pprint(result)

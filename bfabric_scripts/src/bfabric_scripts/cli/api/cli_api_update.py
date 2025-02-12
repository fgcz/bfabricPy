import cyclopts
import rich
import rich.prompt
from cyclopts import Parameter
from loguru import logger
from pydantic import BaseModel
from rich.panel import Panel
from rich.pretty import Pretty, pprint

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client

app = cyclopts.App()


@Parameter(name="*")
class Params(BaseModel):
    endpoint: str
    """Endpoint to update, e.g. 'resource'."""
    entity_id: int
    """ID of the entity to update."""
    attributes: list[tuple[str, str]] | None = None
    """List of attribute-value pairs to update the entity with."""
    no_confirm: bool = False
    """If set, the update will be performed without asking for confirmation."""


@app.default
@use_client
@logger.catch(reraise=True)
def update(params: Params, *, client: Bfabric) -> None:
    """Updates an existing entity in B-Fabric."""
    attributes_dict = _sanitize_attributes(params.attributes, params.entity_id)
    if not attributes_dict:
        return

    if not params.no_confirm:
        if not _confirm_action(attributes_dict, client, params.endpoint, params.entity_id):
            return

    result = client.save(params.endpoint, {"id": params.entity_id, **attributes_dict})
    logger.info(f"Entity with ID {params.entity_id} updated successfully.")
    pprint(result)


def _confirm_action(attributes_dict: dict[str, str], client: Bfabric, endpoint: str, entity_id: int) -> bool:
    logger.info(f"Updating {endpoint} entity with ID {entity_id} with attributes {attributes_dict}")
    result_read = client.read(endpoint, {"id": entity_id}, max_results=1)
    if not result_read:
        raise ValueError(f"No entity found with ID {entity_id}")
    rich.print(Panel.fit(Pretty(result_read[0], expand_all=False), title="Existing entity"))
    rich.print(Panel.fit(Pretty(attributes_dict, expand_all=False), title="Updates"))
    if not rich.prompt.Confirm.ask("Do you want to proceed with the update?"):
        logger.info("Update cancelled by user.")
        return False
    return True


def _sanitize_attributes(attributes: list[tuple[str, str]] | None, entity_id: int) -> dict[str, str] | None:
    if not attributes:
        logger.warning("No attributes provided, doing nothing.")
        return None

    attributes_dict = {attribute: value for attribute, value in attributes}
    if "id" in attributes_dict:
        if int(attributes_dict["id"]) == entity_id:
            logger.warning("Attribute 'id' is not allowed in the attributes, removing it.")
            del attributes_dict["id"]
        else:
            raise ValueError("Attribute 'id' must match the entity_id")
    return attributes_dict

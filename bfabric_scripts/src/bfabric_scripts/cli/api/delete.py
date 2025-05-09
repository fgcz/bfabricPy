import cyclopts
import rich
from loguru import logger
from pydantic import BaseModel
from rich.panel import Panel
from rich.pretty import Pretty
from rich.prompt import Confirm

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client


@cyclopts.Parameter(name="*")
class Params(BaseModel):
    endpoint: str
    """The endpoint to delete from, e.g. 'resource'."""

    id: list[int]
    """The id or ids to delete."""

    no_confirm: bool = False
    """Whether to ask for confirmation before deleting."""


def _perform_delete(client: Bfabric, endpoint: str, id: list[int]) -> None:
    """Deletes the entity with the given id from the given endpoint."""
    client.delete(endpoint=endpoint, id=id)
    logger.info(f"{endpoint.capitalize()} with ID(s) {id} deleted successfully.")


@logger.catch(reraise=True)
@use_client
def cmd_api_delete(params: Params, *, client: Bfabric) -> None:
    """Deletes entities from B-Fabric by id."""
    if params.no_confirm:
        _perform_delete(client=client, endpoint=params.endpoint, id=params.id)
    else:
        existing_entities = client.read(params.endpoint, {"id": params.id})

        for id in params.id:
            existing_entity = next((e for e in existing_entities if e["id"] == id), None)
            if not existing_entity:
                logger.warning(f"No entity found with ID {id}")
                continue

            rich.print(
                Panel.fit(
                    Pretty(existing_entity, expand_all=False), title=f"{params.endpoint.capitalize()} with ID {id}"
                )
            )
            if Confirm.ask(f"Delete {params.endpoint} with ID {id}?"):
                _perform_delete(client=client, endpoint=params.endpoint, id=[id])

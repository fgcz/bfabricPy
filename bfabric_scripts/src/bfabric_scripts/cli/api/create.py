import cyclopts
from cyclopts import Parameter
from loguru import logger
from pydantic import BaseModel, field_validator
from rich.console import Console

from bfabric import Bfabric
from bfabric.utils.cli_integration import use_client
from bfabric_scripts.cli.api.output_format import OutputFormat, render_output
from bfabric_scripts.cli.api.query_repr import Query

app = cyclopts.App()


@Parameter(name="*")
class Params(BaseModel):
    endpoint: str
    """Endpoint to create an entity in, e.g. 'resource'."""
    attributes: Query
    """List of attribute-value pairs for the new entity."""
    format: OutputFormat = OutputFormat.JSON
    """Output format."""

    @field_validator("attributes")
    def _must_not_contain_id(cls, value):
        if value:
            for attribute, _ in value:
                if attribute == "id":
                    raise ValueError("Attribute 'id' is not allowed in the attributes.")
        return value


@app.default
@use_client
def cmd_api_create(params: Params, *, client: Bfabric) -> None:
    """Creates a new entity in B-Fabric."""
    attributes_dict = params.attributes.to_dict(duplicates="error")
    result = client.save(params.endpoint, attributes_dict)
    logger.info(f"{params.endpoint} entity with ID {result[0]['id']} created successfully.")
    _ = render_output(
        result.to_list_dict(),
        output_format=params.format,
        endpoint=params.endpoint,
        client=client,
        console=Console(),
    )

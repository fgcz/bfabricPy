from cyclopts import Parameter
from pydantic import BaseModel
from bfabric.utils.cli_integration import use_client
from loguru import logger
from bfabric import Bfabric

from .parser import parse_method_signature, ParameterModel, FieldModel


@Parameter(name="*")
class Params(BaseModel):
    endpoint: str
    """Endpoint to inspect, e.g. "resource"."""
    method_name: str = "read"
    """Name of the API method to inspect."""
    max_depth: int = 5
    """Maximum recursion depth for nested types."""


def display_signature(signature: dict[str, ParameterModel], indent: int = 0) -> None:
    """Pretty-print a parsed method signature.

    Args:
        signature: Dictionary mapping parameter names to ParameterModel instances
        indent: Base indentation level
    """
    for param_name, param in signature.items():
        print(f"\nParameter: {param_name}")
        print(f"Type: {param.type_name}")

        if param.children:
            _display_fields(param.children, indent=1)


def _display_fields(fields: list[FieldModel], indent: int) -> None:
    """Recursively display fields with proper indentation.

    Args:
        fields: List of FieldModel instances to display
        indent: Current indentation level
    """
    prefix = "  " * indent

    for field in fields:
        required = "required" if field.required else "optional"
        print(f"{prefix}- {field.name}: {field.type} ({required})")

        if field.children:
            _display_fields(field.children, indent + 1)


@use_client
@logger.catch(reraise=True)
def cmd_api_inspect(params: Params, *, client: Bfabric) -> None:
    """Inspect and display the parameter structure of a SOAP endpoint method.

    Please note that this information is read from the SOAP API and does not in all cases directly
    translate to BfabricPy functionality.
    """
    signature = parse_method_signature(
        client=client,
        endpoint=params.endpoint,
        method_name=params.method_name,
        max_depth=params.max_depth,
    )
    display_signature(signature)

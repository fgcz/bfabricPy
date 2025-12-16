from cyclopts import Parameter
from pydantic import BaseModel
from bfabric.utils.cli_integration import use_client
from loguru import logger
from bfabric import Bfabric
from rich.console import Console

from .parser import parse_method_signature, ParameterModel, FieldModel
from .namespaces import NAMESPACES, NAMESPACE_URIS

console = Console()


@Parameter(name="*")
class Params(BaseModel):
    endpoint: str
    """Endpoint to inspect, e.g. "resource"."""
    method_name: str = "read"
    """Name of the API method to inspect."""
    max_depth: int = 5
    """Maximum recursion depth for nested types."""


def _collect_namespaces(signature: dict[str, ParameterModel]) -> dict[str, str]:
    """Collect all unique namespaces from the signature and assign prefixes."""
    namespaces_set: set[str] = set()
    for param in signature.values():
        _collect_namespaces_from_fields(param.children, namespaces_set)

    # Start with known namespaces
    namespaces = {prefix: uri for prefix, uri in NAMESPACES.items() if uri in namespaces_set}

    # Add unknown namespaces with generic prefixes
    counter = 0
    for ns in sorted(namespaces_set - set(NAMESPACE_URIS.keys())):
        namespaces[f"ns{counter}"] = ns
        counter += 1

    return namespaces


def _collect_namespaces_from_fields(fields: list[FieldModel], namespaces_set: set[str]) -> None:
    """Recursively collect namespaces from fields.

    Args:
        fields: List of FieldModel instances
        namespaces_set: Set to collect namespace URIs
    """
    for field in fields:
        if isinstance(field.type, tuple) and len(field.type) == 2:
            _, namespace = field.type
            namespaces_set.add(namespace)

        if field.children:
            _collect_namespaces_from_fields(field.children, namespaces_set)


def _format_type(field_type: str | tuple[str, str]) -> str:
    """Format a field type with namespace prefix."""
    if isinstance(field_type, tuple) and len(field_type) == 2:
        type_name, namespace_uri = field_type
        prefix = NAMESPACE_URIS.get(namespace_uri, "")
        return f"{prefix}:{type_name}" if prefix else type_name
    return str(field_type)


def display_signature(signature: dict[str, ParameterModel]) -> None:
    """Pretty-print a parsed method signature with Rich formatting.

    Args:
        signature: Dictionary mapping parameter names to ParameterModel instances
    """
    # Collect all namespaces used in the signature
    namespaces = _collect_namespaces(signature)

    # Display namespace mappings
    if namespaces:
        console.print("\n[bold]Namespaces:[/bold]")
        for prefix, uri in sorted(namespaces.items()):
            console.print(f"  {prefix}: [dim]{uri}[/dim]")

    for param_name, param in signature.items():
        console.print(f"\n[bold]Parameter:[/bold] {param_name}")
        console.print(f"[bold]Type:[/bold] {param.type_name}")

        if param.children:
            _display_fields(param.children, indent=1)

        console.print("\n[red]*[/red] required")


def _display_fields(fields: list[FieldModel], indent: int) -> None:
    """Recursively display fields with proper indentation and Rich formatting."""
    prefix = "  " * indent

    for field in fields:
        # Format the type with namespace prefix
        formatted_type = _format_type(field.type)

        # Add [] suffix for multi-occurrence fields (lists)
        if field.multi_occurrence:
            formatted_type = f"{formatted_type}[]"

        # Add red asterisk for required fields
        required_marker = " [red]*[/red]" if field.required else ""

        console.print(f"{prefix}- {field.name}: [italic]{formatted_type}[/italic]{required_marker}")

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

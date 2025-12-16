from cyclopts import Parameter
from pydantic import BaseModel
from bfabric.utils.cli_integration import use_client
from loguru import logger
from bfabric import Bfabric
from rich.console import Console

from .parser import parse_method_signature, ParameterModel, FieldModel

console = Console()


# Standard XSD namespace
XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"


@Parameter(name="*")
class Params(BaseModel):
    endpoint: str
    """Endpoint to inspect, e.g. "resource"."""
    method_name: str = "read"
    """Name of the API method to inspect."""
    max_depth: int = 5
    """Maximum recursion depth for nested types."""


def _collect_namespaces(signature: dict[str, ParameterModel]) -> dict[str, str]:
    """Collect all unique namespaces from the signature and assign prefixes.

    Args:
        signature: Dictionary mapping parameter names to ParameterModel instances

    Returns:
        Dictionary mapping namespace prefixes to URIs
    """
    namespaces_set: set[str] = set()

    # Collect namespaces from all parameters and fields
    for param in signature.values():
        _collect_namespaces_from_fields(param.children, namespaces_set)

    # Create prefix mappings
    namespaces: dict[str, str] = {}
    namespace_counter = 0

    for ns in sorted(namespaces_set):
        if ns == XSD_NAMESPACE:
            namespaces["xs"] = ns
        else:
            # Use a generic prefix for other namespaces
            # Extract a meaningful prefix from the URL if possible
            if "bfabric" in ns.lower():
                namespaces["bf"] = ns
            else:
                namespaces[f"ns{namespace_counter}"] = ns
                namespace_counter += 1

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


def _format_type(field_type: str | tuple[str, str], namespaces: dict[str, str]) -> str:
    """Format a field type with namespace prefix.

    Args:
        field_type: Either a string or tuple of (type_name, namespace_uri)
        namespaces: Dictionary mapping namespace prefixes to URIs

    Returns:
        Formatted type string with prefix
    """
    if isinstance(field_type, tuple) and len(field_type) == 2:
        type_name, namespace_uri = field_type

        # Find the prefix for this namespace
        for prefix, uri in namespaces.items():
            if uri == namespace_uri:
                return f"{prefix}:{type_name}"

        # Fallback if namespace not found in mapping
        return type_name

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
            _display_fields(param.children, namespaces, indent=1)

        console.print("\n[red]*[/red] required")


def _display_fields(fields: list[FieldModel], namespaces: dict[str, str], indent: int) -> None:
    """Recursively display fields with proper indentation and Rich formatting.

    Args:
        fields: List of FieldModel instances to display
        namespaces: Dictionary mapping namespace prefixes to URIs
        indent: Current indentation level
    """
    prefix = "  " * indent

    for field in fields:
        # Format the type with namespace prefix
        formatted_type = _format_type(field.type, namespaces)

        # Add red asterisk for required fields
        required_marker = " [red]*[/red]" if field.required else ""

        console.print(f"{prefix}- {field.name}: [italic]{formatted_type}[/italic]{required_marker}")

        if field.children:
            _display_fields(field.children, namespaces, indent + 1)


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

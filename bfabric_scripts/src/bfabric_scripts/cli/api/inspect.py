from cyclopts import Parameter
from pydantic import BaseModel
from suds.xsd.query import TypeQuery
from bfabric.utils.cli_integration import use_client
from loguru import logger
from bfabric import Bfabric


def display_type_tree(field_type: tuple[str, str] | str, schema, indent: int = 0, max_depth: int = 5) -> None:
    """Recursively display a type and its nested fields.

    Args:
        field_type: Type reference (tuple of (name, namespace) or string)
        schema: SUDS schema object
        indent: Current indentation level
        max_depth: Maximum recursion depth
    """
    if indent > max_depth:
        return

    prefix = "  " * indent

    # Handle tuple type references like ('xmlRequestParameterReadImportResource', 'http://...')
    if isinstance(field_type, tuple):
        type_name, type_ns = field_type

        # Skip builtin types
        if type_ns == "http://www.w3.org/2001/XMLSchema":
            return

        # Look up the type in the schema
        query = TypeQuery(field_type)
        type_def = query.execute(schema)

        if type_def:
            resolved = type_def.resolve()
            print(f"{prefix}→ {type_name}:")

            if hasattr(resolved, "children"):
                fields = resolved.children()
                for field, ancestry in fields:
                    required = "required" if (hasattr(field, "minOccurs") and field.minOccurs > 0) else "optional"
                    field_type_info = field.type if hasattr(field, "type") else "N/A"
                    print(f"{prefix}  - {field.name}: {field_type_info} ({required})")

                    # Recurse for nested types
                    if hasattr(field, "type"):
                        display_type_tree(field.type, schema, indent + 2, max_depth)


@Parameter(name="*")
class Params(BaseModel):
    endpoint: str
    """Endpoint to inspect, e.g. "resource"."""
    method_name: str = "read"
    """Name of the API method to inspect."""
    max_depth: int = 5
    """Maximum recursion depth for nested types."""


@use_client
@logger.catch(reraise=True)
def cmd_api_inspect(params: Params, *, client: Bfabric) -> None:
    """Inspect and display the parameter structure of a SOAP endpoint method.

    Please note that this information is read from the SOAP API and does not in all cases directly
    translate to BfabricPy functionality.
    """
    inspect_endpoint(
        client=client, endpoint=params.endpoint, method_name=params.method_name, max_depth=params.max_depth
    )


def inspect_endpoint(client: Bfabric, endpoint: str, method_name: str, max_depth: int = 5) -> None:
    """Inspect and display the parameter structure of a SOAP endpoint method.

    Args:
        client: Initialized Bfabric client with _engine attribute
        endpoint: Name of the endpoint to inspect (e.g., "importresource")
        method_name: Name of the method to inspect (e.g.: "read")
        max_depth: Maximum recursion depth for nested types (default: 5)
    """
    # Get the SUDS service
    service = client._engine._get_suds_service(endpoint)

    # Get the specified method
    method = getattr(service, method_name)

    # Get parameter definitions
    binding = method.method.binding.input
    param_defs = binding.param_defs(method.method)

    # Get schema for type resolution
    schema = method.method.binding.input.wsdl.schema

    # Display parameters with recursive type information
    for param_name, param_schema in param_defs:
        print(f"\nParameter: {param_name}")

        resolved_type = param_schema.resolve()
        print(f"Type: {resolved_type.name}")

        if hasattr(resolved_type, "children"):
            fields = resolved_type.children()
            for field, ancestry in fields:
                required = "required" if (hasattr(field, "minOccurs") and field.minOccurs > 0) else "optional"
                field_type_info = field.type if hasattr(field, "type") else "N/A"
                print(f"  - {field.name}: {field_type_info} ({required})")

                # Recurse for nested types
                if hasattr(field, "type"):
                    display_type_tree(field.type, schema, indent=2, max_depth=max_depth)

"""Parser for SOAP API method signatures using SUDS.

Extracts parameter and type information from SOAP endpoints into reusable
Pydantic models for introspection and programmatic access.
"""

from pydantic import BaseModel, Field, ConfigDict
from suds.xsd.query import TypeQuery
from bfabric import Bfabric


class FieldModel(BaseModel):
    """Represents a single field in a type definition."""

    name: str
    type: str | tuple[str, str]
    required: bool
    children: list["FieldModel"] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ParameterModel(BaseModel):
    """Represents a complete parameter with its type structure."""

    name: str
    type_name: str
    required: bool
    children: list[FieldModel] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)


def parse_method_signature(
    client: Bfabric,
    endpoint: str,
    method_name: str,
    max_depth: int = 5,
) -> dict[str, ParameterModel]:
    """Parse a SOAP method signature into reusable Pydantic models.

    Args:
        client: Initialized Bfabric client with _engine attribute
        endpoint: Name of the endpoint to inspect (e.g., "importresource")
        method_name: Name of the method to inspect (e.g., "read")
        max_depth: Maximum recursion depth for nested types

    Returns:
        Dictionary mapping parameter names to ParameterModel instances.

    Raises:
        AttributeError: If endpoint or method doesn't exist
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

    # Parse each parameter
    result = {}
    for param_name, param_schema in param_defs:
        resolved_type = param_schema.resolve()
        type_name = resolved_type.name if hasattr(resolved_type, "name") else str(resolved_type)

        # Parse nested fields
        children = []
        if hasattr(resolved_type, "children"):
            fields = resolved_type.children()
            for field, _ancestry in fields:
                child_field = _parse_field_recursive(field, schema, current_depth=0, max_depth=max_depth)
                children.append(child_field)

        result[param_name] = ParameterModel(
            name=param_name,
            type_name=type_name,
            required=True,  # Top-level parameters are typically required
            children=children,
        )

    return result


def _parse_field_recursive(
    field,
    schema,
    current_depth: int,
    max_depth: int,
) -> FieldModel:
    """Recursively parse a field and its nested types.

    Args:
        field: SUDS field object
        schema: SUDS schema object for type resolution
        current_depth: Current recursion depth
        max_depth: Maximum recursion depth

    Returns:
        FieldModel with fully resolved nested structure
    """
    # Extract field information
    field_name = field.name if hasattr(field, "name") else "unknown"
    field_type = field.type if hasattr(field, "type") else "N/A"
    required = hasattr(field, "minOccurs") and field.minOccurs > 0

    children = []

    # Recurse into nested types if within depth limit
    if current_depth < max_depth and hasattr(field, "type"):
        type_ref = field.type

        # Skip built-in XML types
        if isinstance(type_ref, tuple):
            type_name, type_ns = type_ref
            if type_ns != "http://www.w3.org/2001/XMLSchema":
                # Look up the type in the schema
                query = TypeQuery(type_ref)
                type_def = query.execute(schema)

                if type_def:
                    resolved = type_def.resolve()
                    if hasattr(resolved, "children"):
                        nested_fields = resolved.children()
                        for nested_field, _ancestry in nested_fields:
                            child_field = _parse_field_recursive(nested_field, schema, current_depth + 1, max_depth)
                            children.append(child_field)

    return FieldModel(
        name=field_name,
        type=field_type,
        required=required,
        children=children,
    )

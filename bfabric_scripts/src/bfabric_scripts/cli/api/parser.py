"""Parser for SOAP API method signatures using SUDS.

Extracts parameter and type information from SOAP endpoints into reusable
Pydantic models for introspection and programmatic access.

Note: This module deals with SUDS, which has limited type stubs. Many type
checks are suppressed here as they relate to the SUDS library's dynamic nature.
This module deeply interacts with SUDS internals and type checking is disabled.
"""

# pyright: basic

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from suds.xsd.query import TypeQuery  # pyright: ignore[reportMissingTypeStubs]

from bfabric import Bfabric


class FieldModel(BaseModel):
    """Represents a single field in a type definition."""

    name: str
    type: str | tuple[str, str]
    required: bool
    multi_occurrence: bool
    children: list["FieldModel"] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)  # pyright: ignore[reportUnannotatedClassAttribute]


class ParameterModel(BaseModel):
    """Represents a complete parameter with its type structure."""

    name: str
    type_name: str
    required: bool
    children: list[FieldModel] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)  # pyright: ignore[reportUnannotatedClassAttribute]


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
    # Note: This only works with EngineSuds, not EngineZeep
    service = client._engine._get_suds_service(endpoint)  # type: ignore[attr-defined]  # pyright: ignore[reportPrivateUsage,reportAttributeAccessIssue,reportUnknownVariableType,reportUnknownMemberType]

    # Get the specified method
    method = getattr(service, method_name)  # pyright: ignore[reportAny,reportUnknownArgumentType]

    # Get parameter definitions
    binding = method.method.binding.input  # pyright: ignore[reportAny]
    param_defs = binding.param_defs(method.method)  # pyright: ignore[reportAny]

    # Get schema for type resolution
    schema = method.method.binding.input.wsdl.schema  # pyright: ignore[reportAny]

    # Parse each parameter
    result: dict[str, ParameterModel] = {}
    for param_name, param_schema in param_defs:  # pyright: ignore[reportAny]
        resolved_type = param_schema.resolve()  # pyright: ignore[reportAny]
        type_name: str = (
            resolved_type.name  # pyright: ignore[reportAny]
            if hasattr(resolved_type, "name")  # pyright: ignore[reportAny]
            else str(resolved_type)  # pyright: ignore[reportAny]
        )

        # Parse nested fields
        children: list[FieldModel] = []
        if hasattr(resolved_type, "children"):  # pyright: ignore[reportAny]
            fields = resolved_type.children()  # pyright: ignore[reportAny]
            for field, _ancestry in fields:  # pyright: ignore[reportAny]
                child_field = _parse_field_recursive(field, schema, current_depth=0, max_depth=max_depth)
                children.append(child_field)

        result[param_name] = ParameterModel(
            name=param_name,  # pyright: ignore[reportAny]
            type_name=type_name,
            # Use SUDS built-in method to check if required, fallback to True (XSD default when minOccurs not specified)
            required=(
                resolved_type.required() if hasattr(resolved_type, "required") else True  # pyright: ignore[reportAny]
            ),
            children=children,
        )

    return result


def _parse_field_recursive(
    field: Any,  # pyright: ignore[reportExplicitAny,reportAny]
    schema: Any,  # pyright: ignore[reportExplicitAny,reportAny]
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
    field_name: str = field.name if hasattr(field, "name") else "unknown"  # pyright: ignore[reportAny]
    field_type: str | tuple[str, str] = field.type if hasattr(field, "type") else "N/A"  # pyright: ignore[reportAny]
    # Use SUDS built-in method to check if required, fallback to True (XSD default when minOccurs not specified)
    required: bool = field.required() if hasattr(field, "required") else True  # pyright: ignore[reportAny]
    # Check if multiple occurrences are allowed (maxOccurs > 1 or maxOccurs = "unbounded")
    multi_occurrence: bool = (
        field.multi_occurrence() if hasattr(field, "multi_occurrence") else False
    )  # pyright: ignore[reportAny]

    children: list[FieldModel] = []

    # Recurse into nested types if within depth limit
    if current_depth < max_depth and hasattr(field, "type"):  # pyright: ignore[reportAny]
        type_ref = field.type  # pyright: ignore[reportAny]

        # Skip built-in XML types
        if isinstance(type_ref, tuple):
            _type_name, type_ns = type_ref  # pyright: ignore[reportUnknownVariableType]
            if type_ns != "http://www.w3.org/2001/XMLSchema":
                # Look up the type in the schema
                query = TypeQuery(type_ref)
                type_def = query.execute(
                    schema
                )  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType,reportAny]

                if type_def:
                    resolved = type_def.resolve()  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                    if hasattr(resolved, "children"):  # pyright: ignore[reportUnknownArgumentType]
                        nested_fields = (
                            resolved.children()
                        )  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                        for nested_field, _ancestry in nested_fields:  # pyright: ignore[reportUnknownVariableType]
                            child_field = _parse_field_recursive(nested_field, schema, current_depth + 1, max_depth)
                            children.append(child_field)

    return FieldModel(
        name=field_name,
        type=field_type,
        required=required,
        multi_occurrence=multi_occurrence,
        children=children,
    )

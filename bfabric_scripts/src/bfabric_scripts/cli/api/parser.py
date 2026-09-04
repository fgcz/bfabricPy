"""Parses SOAP method signatures into Pydantic models for ``api inspect``.

Written against SUDS internals, whose limited type stubs are why this module runs at
``# pyright: basic`` with per-line ignores.
"""

# pyright: basic

from typing import Any

from pydantic import BaseModel, Field
from suds.xsd.query import TypeQuery  # pyright: ignore[reportMissingTypeStubs]

from bfabric import Bfabric
from bfabric.config.bfabric_client_config import BfabricAPIEngineType

from bfabric_scripts.cli.api.namespaces import NAMESPACES


class FieldModel(BaseModel):
    """Represents a single field in a type definition."""

    name: str
    type: str | tuple[str, str]
    required: bool
    multi_occurrence: bool
    children: list["FieldModel"] = Field(default_factory=list)


class ParameterModel(BaseModel):
    """Represents a complete parameter with its type structure."""

    name: str
    type_name: str
    required: bool
    children: list[FieldModel] = Field(default_factory=list)


def parse_method_signature(
    client: Bfabric,
    endpoint: str,
    method_name: str,
    max_depth: int = 5,
) -> dict[str, ParameterModel]:
    """Parses a SOAP method signature into reusable Pydantic models.

    :raises RuntimeError: If the client is not configured to use the SUDS engine.
    :raises AttributeError: If the endpoint or method does not exist.
    """
    # The WSDL introspection below is written against SUDS internals, so reject any other engine up
    # front instead of leaking an AttributeError from the private engine.
    if client.config.engine != BfabricAPIEngineType.SUDS:
        raise RuntimeError(
            f"'api inspect' is only supported with the SUDS engine (got: {client.config.engine}). "
            f"Set engine: SUDS in your bfabricpy config."
        )

    service = client._engine._get_suds_service(endpoint)  # type: ignore[attr-defined]  # pyright: ignore[reportPrivateUsage,reportAttributeAccessIssue,reportUnknownVariableType,reportUnknownMemberType]

    method = getattr(service, method_name)  # pyright: ignore[reportAny,reportUnknownArgumentType]

    binding = method.method.binding.input  # pyright: ignore[reportAny]
    param_defs = binding.param_defs(method.method)  # pyright: ignore[reportAny]

    schema = method.method.binding.input.wsdl.schema  # pyright: ignore[reportAny]

    result: dict[str, ParameterModel] = {}
    for param_name, param_schema in param_defs:  # pyright: ignore[reportAny]
        resolved_type = param_schema.resolve()  # pyright: ignore[reportAny]
        type_name: str = (
            resolved_type.name  # pyright: ignore[reportAny]
            if hasattr(resolved_type, "name")  # pyright: ignore[reportAny]
            else str(resolved_type)  # pyright: ignore[reportAny]
        )

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
    """Recursively parses a field and its nested types."""
    field_name: str = field.name if hasattr(field, "name") else "unknown"  # pyright: ignore[reportAny]
    field_type: str | tuple[str, str] = field.type if hasattr(field, "type") else "N/A"  # pyright: ignore[reportAny]
    # Use SUDS built-in method to check if required, fallback to True (XSD default when minOccurs not specified)
    required: bool = field.required() if hasattr(field, "required") else True  # pyright: ignore[reportAny]
    # Check if multiple occurrences are allowed (maxOccurs > 1 or maxOccurs = "unbounded")
    multi_occurrence: bool = (
        field.multi_occurrence() if hasattr(field, "multi_occurrence") else False
    )  # pyright: ignore[reportAny]

    children: list[FieldModel] = []

    if current_depth < max_depth and hasattr(field, "type"):  # pyright: ignore[reportAny]
        type_ref = field.type  # pyright: ignore[reportAny]

        if isinstance(type_ref, tuple):
            _type_name, type_ns = type_ref  # pyright: ignore[reportUnknownVariableType]
            if type_ns != NAMESPACES["xs"]:
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

"""Tests for the API parser module."""

from __future__ import annotations

import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock

from bfabric_scripts.cli.api.parser import (
    FieldModel,
    ParameterModel,
    parse_method_signature,
    _parse_field_recursive,
)


class TestFieldModel:
    """Tests for FieldModel Pydantic model."""

    def test_field_model_creation(self) -> None:
        """Test basic FieldModel creation."""
        field = FieldModel(
            name="test_field",
            type="string",
            required=True,
            multi_occurrence=False,
            children=[],
        )
        assert field.name == "test_field"
        assert field.type == "string"
        assert field.required is True
        assert field.multi_occurrence is False
        assert field.children == []

    def test_field_model_with_tuple_type(self) -> None:
        """Test FieldModel with tuple type reference."""
        field = FieldModel(
            name="nested_field",
            type=("CustomType", "http://example.com/schema"),
            required=False,
            multi_occurrence=False,
            children=[],
        )
        assert field.name == "nested_field"
        assert field.type == ("CustomType", "http://example.com/schema")
        assert field.required is False
        assert field.multi_occurrence is False

    def test_field_model_with_children(self) -> None:
        """Test FieldModel with nested children."""
        child = FieldModel(name="child", type="int", required=False, multi_occurrence=False, children=[])
        parent = FieldModel(
            name="parent",
            type="complex_type",
            required=True,
            multi_occurrence=False,
            children=[child],
        )
        assert len(parent.children) == 1
        assert parent.children[0].name == "child"

    def test_field_model_serialization(self) -> None:
        """Test FieldModel can be serialized to dict."""
        field = FieldModel(name="test", type="string", required=True, multi_occurrence=False, children=[])
        field_dict = field.model_dump()
        assert field_dict["name"] == "test"
        assert field_dict["type"] == "string"
        assert field_dict["required"] is True
        assert field_dict["multi_occurrence"] is False


class TestParameterModel:
    """Tests for ParameterModel Pydantic model."""

    def test_parameter_model_creation(self) -> None:
        """Test basic ParameterModel creation."""
        param = ParameterModel(
            name="param1",
            type_name="ParamType",
            required=True,
            children=[],
        )
        assert param.name == "param1"
        assert param.type_name == "ParamType"
        assert param.required is True
        assert param.children == []

    def test_parameter_model_with_children(self) -> None:
        """Test ParameterModel with nested fields."""
        field = FieldModel(name="field1", type="string", required=False, multi_occurrence=False, children=[])
        param = ParameterModel(
            name="param1",
            type_name="ComplexType",
            required=True,
            children=[field],
        )
        assert len(param.children) == 1
        assert param.children[0].name == "field1"


class TestParseFieldRecursive:
    """Tests for _parse_field_recursive function."""

    def test_parse_simple_field(self) -> None:
        """Test parsing a simple field without children."""
        field_mock = MagicMock()
        field_mock.name = "simple_field"
        field_mock.type = "string"
        field_mock.required.return_value = False
        field_mock.multi_occurrence.return_value = False

        schema_mock = MagicMock()

        result = _parse_field_recursive(field_mock, schema_mock, current_depth=0, max_depth=5)

        assert result.name == "simple_field"
        assert result.type == "string"
        assert result.required is False
        assert result.multi_occurrence is False
        assert result.children == []

    def test_parse_required_field(self) -> None:
        """Test parsing a field marked as required."""
        field_mock = MagicMock()
        field_mock.name = "required_field"
        field_mock.type = "int"
        field_mock.required.return_value = True
        field_mock.multi_occurrence.return_value = False

        schema_mock = MagicMock()

        result = _parse_field_recursive(field_mock, schema_mock, current_depth=0, max_depth=5)

        assert result.name == "required_field"
        assert result.required is True
        assert result.multi_occurrence is False

    def test_parse_field_max_depth_exceeded(self) -> None:
        """Test that recursion stops at max_depth."""
        field_mock = MagicMock()
        field_mock.name = "field"
        field_mock.type = "string"
        field_mock.required.return_value = False
        field_mock.multi_occurrence.return_value = False

        schema_mock = MagicMock()

        # At max depth, should not recurse even if type exists
        result = _parse_field_recursive(field_mock, schema_mock, current_depth=5, max_depth=5)

        assert result.name == "field"
        assert result.children == []

    def test_parse_field_skips_builtin_types(self) -> None:
        """Test that built-in XML Schema types are skipped."""
        field_mock = MagicMock()
        field_mock.name = "xml_field"
        field_mock.type = ("string", "http://www.w3.org/2001/XMLSchema")
        field_mock.required.return_value = False
        field_mock.multi_occurrence.return_value = False

        schema_mock = MagicMock()

        result = _parse_field_recursive(field_mock, schema_mock, current_depth=0, max_depth=5)

        # Should not recurse into builtin XML types
        assert result.children == []

    def test_parse_field_with_nested_type(self, mocker: MockerFixture) -> None:
        """Test parsing a field with nested custom type."""
        # Create nested field
        nested_field_mock = MagicMock()
        nested_field_mock.name = "nested_field"
        nested_field_mock.type = "simple_type"
        nested_field_mock.required.return_value = False
        nested_field_mock.multi_occurrence.return_value = False

        # Create parent field with custom type
        parent_field_mock = MagicMock()
        parent_field_mock.name = "parent_field"
        parent_field_mock.type = ("CustomType", "http://example.com/schema")
        parent_field_mock.required.return_value = False
        parent_field_mock.multi_occurrence.return_value = False

        # Mock schema and type resolution
        schema_mock = MagicMock()

        resolved_type_mock = MagicMock()
        resolved_type_mock.children.return_value = [(nested_field_mock, None)]

        type_def_mock = MagicMock()
        type_def_mock.resolve.return_value = resolved_type_mock

        # Mock TypeQuery
        mocker.patch(
            "bfabric_scripts.cli.api.parser.TypeQuery",
            return_value=MagicMock(execute=MagicMock(return_value=type_def_mock)),
        )

        result = _parse_field_recursive(parent_field_mock, schema_mock, current_depth=0, max_depth=5)

        assert result.name == "parent_field"
        assert len(result.children) == 1
        assert result.children[0].name == "nested_field"


class TestParseMethodSignature:
    """Tests for parse_method_signature function."""

    def test_parse_method_signature_basic(self, mocker: MockerFixture) -> None:
        """Test basic method signature parsing."""
        # Mock parameter field
        param_field_mock = MagicMock()
        param_field_mock.name = "field1"
        param_field_mock.type = "string"
        param_field_mock.required.return_value = False
        param_field_mock.multi_occurrence.return_value = False

        # Mock parameter schema
        param_schema_mock = MagicMock()
        resolved_param_mock = MagicMock()
        resolved_param_mock.name = "ParamType"
        resolved_param_mock.required.return_value = True
        resolved_param_mock.children.return_value = [(param_field_mock, None)]
        param_schema_mock.resolve.return_value = resolved_param_mock

        # Mock method binding
        binding_mock = MagicMock()
        binding_mock.param_defs.return_value = [("testParam", param_schema_mock)]

        # Mock method
        method_mock = MagicMock()
        method_mock.method.binding.input = binding_mock
        method_mock.method.binding.input.wsdl.schema = MagicMock()

        # Mock service
        service_mock = MagicMock()
        service_mock.testMethod = MagicMock(method=method_mock.method)
        mocker.patch.object(service_mock, "testMethod", method_mock)

        # Mock client
        client_mock = MagicMock()
        client_mock._engine._get_suds_service.return_value = service_mock
        mocker.patch.object(service_mock, "testMethod", method_mock)
        client_mock._engine._get_suds_service.return_value = MagicMock(testMethod=method_mock)

        # Call function
        result = parse_method_signature(client_mock, "test_endpoint", "testMethod")

        # Verify structure
        assert "testParam" in result
        assert result["testParam"].name == "testParam"
        assert result["testParam"].type_name == "ParamType"
        assert len(result["testParam"].children) == 1
        assert result["testParam"].children[0].name == "field1"

    def test_parse_method_signature_empty_parameters(self, mocker: MockerFixture) -> None:
        """Test parsing a method with no parameters."""
        # Mock method with no parameters
        binding_mock = MagicMock()
        binding_mock.param_defs.return_value = []

        method_mock = MagicMock()
        method_mock.method.binding.input = binding_mock
        method_mock.method.binding.input.wsdl.schema = MagicMock()

        # Mock service and client
        service_mock = MagicMock()
        service_mock.testMethod = method_mock

        client_mock = MagicMock()
        client_mock._engine._get_suds_service.return_value = service_mock

        # Call function
        result = parse_method_signature(client_mock, "test_endpoint", "testMethod")

        # Should return empty dict
        assert result == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

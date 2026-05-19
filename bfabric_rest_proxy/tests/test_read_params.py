"""Unit tests for ReadParams model validation.

This module tests the ReadParams Pydantic model, ensuring that:
- Empty list [] is converted to empty dict {} (issue #459)
- Empty dict {} remains as empty dict
- Various query value types work correctly
- Invalid query types are rejected
"""

import datetime

import pytest
from bfabric_rest_proxy.server import ReadParams


class TestReadParamsEmptyQuery:
    """Tests for empty query handling - validates fix for issue #459."""

    def test_empty_list_converts_to_empty_dict(self):
        """Test that empty list [] is converted to empty dict {}.

        This is the key fix for issue #459 where R clients send [] instead of {}.
        """
        params = ReadParams(endpoint="screen", query=[])
        assert params.query == {}

    def test_json_empty_list_converts_to_empty_dict(self):
        """Test JSON with empty list [] is converted to empty dict {}."""
        params = ReadParams.model_validate({"endpoint": "screen", "query": []})
        assert params.query == {}

    def test_empty_dict_remains_empty_dict(self):
        """Test that empty dict {} remains as empty dict."""
        params = ReadParams(endpoint="screen", query={})
        assert params.query == {}

    def test_default_query_is_empty_dict(self):
        """Test that default (no query parameter) is empty dict."""
        params = ReadParams(endpoint="screen")
        assert params.query == {}


class TestReadParamsQueryValues:
    """Tests for various query value types."""

    def test_query_with_string_values(self):
        """Test query with string values."""
        params = ReadParams(endpoint="screen", query={"name": "test"})
        assert params.query == {"name": "test"}

    def test_query_with_int_values(self):
        """Test query with integer values."""
        params = ReadParams(endpoint="screen", query={"id": 123})
        assert params.query == {"id": 123}

    def test_query_with_datetime_values(self):
        """Test query with datetime values."""
        dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
        params = ReadParams(endpoint="screen", query={"created": dt})
        assert params.query == {"created": dt}

    def test_query_with_list_values(self):
        """Test query with list values (for OR queries)."""
        params = ReadParams(endpoint="screen", query={"id": [1, 2, 3]})
        assert params.query == {"id": [1, 2, 3]}

    def test_query_with_mixed_types(self):
        """Test query with mixed value types."""
        dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
        params = ReadParams(
            endpoint="screen",
            query={
                "name": "test",
                "id": 123,
                "created": dt,
                "status": ["active", "pending"],
            },
        )
        assert params.query["name"] == "test"
        assert params.query["id"] == 123
        assert params.query["created"] == dt
        assert params.query["status"] == ["active", "pending"]


class TestReadParamsValidation:
    """Tests for parameter validation."""

    def test_endpoint_required(self):
        """Test that endpoint is required."""
        with pytest.raises(Exception):
            ReadParams(query={"id": 1})

    def test_page_offset_default(self):
        """Test default page_offset value."""
        params = ReadParams(endpoint="screen")
        assert params.page_offset == 0

    def test_page_max_results_default(self):
        """Test default page_max_results value."""
        params = ReadParams(endpoint="screen")
        assert params.page_max_results == 100

    def test_page_offset_can_be_set(self):
        """Test that page_offset can be set."""
        params = ReadParams(endpoint="screen", page_offset=10)
        assert params.page_offset == 10

    def test_page_max_results_can_be_set(self):
        """Test that page_max_results can be set."""
        params = ReadParams(endpoint="screen", page_max_results=50)
        assert params.page_max_results == 50


class TestReadParamsInvalidQueries:
    """Tests for invalid query types that should be rejected."""

    def test_query_string_rejected(self):
        """Test that string query is rejected."""
        with pytest.raises(Exception):
            ReadParams(endpoint="screen", query="invalid")

    def test_query_number_rejected(self):
        """Test that number query is rejected."""
        with pytest.raises(Exception):
            ReadParams(endpoint="screen", query=123)

    def test_query_none_rejected(self):
        """Test that None query is rejected (must use default or empty dict)."""
        # Note: Pydantic should reject None since query has a default_factory
        with pytest.raises(Exception):
            ReadParams(endpoint="screen", query=None)

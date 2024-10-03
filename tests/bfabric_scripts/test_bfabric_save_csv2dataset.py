import pytest
import polars as pl

from bfabric_scripts.bfabric_save_csv2dataset import check_for_invalid_characters


def test_check_for_invalid_characters_no_invalid_chars():
    data = pl.DataFrame({"col1": ["abc", "def", "ghi"], "col2": ["123", "456", "789"]})
    invalid_characters = "!@#"

    # Should not raise an exception
    check_for_invalid_characters(data, invalid_characters)


def test_check_for_invalid_characters_with_invalid_chars():
    data = pl.DataFrame({"col1": ["abc", "d!ef", "ghi"], "col2": ["123", "456", "789"]})
    invalid_characters = "!@#"

    with pytest.raises(RuntimeError) as excinfo:
        check_for_invalid_characters(data, invalid_characters)

    assert "Invalid characters found in columns: ['col1']" in str(excinfo.value)


def test_check_for_invalid_characters_multiple_columns():
    data = pl.DataFrame({"col1": ["abc", "d!ef", "ghi"], "col2": ["123", "45@6", "789"], "col3": ["xyz", "uvw", "rst"]})
    invalid_characters = "!@#"

    with pytest.raises(RuntimeError) as excinfo:
        check_for_invalid_characters(data, invalid_characters)

    assert "Invalid characters found in columns: ['col1', 'col2']" in str(excinfo.value)


def test_check_for_invalid_characters_empty_invalid_chars():
    data = pl.DataFrame({"col1": ["abc", "def", "ghi"], "col2": ["123", "456", "789"]})
    invalid_characters = ""

    # Should not raise an exception
    check_for_invalid_characters(data, invalid_characters)


def test_check_for_invalid_characters_empty_dataframe():
    data = pl.DataFrame()
    invalid_characters = "!@#"

    # Should not raise an exception
    check_for_invalid_characters(data, invalid_characters)


def test_check_for_invalid_characters_non_string_columns():
    data = pl.DataFrame({"col1": [1, 2, 3], "col2": [4.5, 5.6, 6.7], "col3": ["abc", "def", "ghi"]})
    invalid_characters = "!@#"

    # Should not raise an exception
    check_for_invalid_characters(data, invalid_characters)


if __name__ == "__main__":
    pytest.main()

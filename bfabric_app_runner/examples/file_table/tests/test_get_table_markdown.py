import polars as pl
from file_table_app.collect_info import get_table_markdown


def test_get_table_markdown() -> None:
    """Test the get_table_markdown function with a simple DataFrame."""
    long_string = "x" * 100
    df = pl.DataFrame({"a": [1, 2, 3], "b": [long_string, long_string, long_string]})
    markdown = get_table_markdown(df)
    assert markdown.startswith("| a")
    assert markdown.endswith("|")
    assert markdown.count(long_string) == 3

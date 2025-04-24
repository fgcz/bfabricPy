from pathlib import Path

import polars as pl
import yaml


def _collect_info(input_files: list[Path | str]) -> pl.DataFrame:
    """Loads the input file contents and returns it as a polars DataFrame."""
    input_files = [Path(f) for f in input_files]
    input_rows = [yaml.safe_load(input_file.read_text()) for input_file in input_files]
    return pl.DataFrame(input_rows)


def get_table_markdown(table: pl.DataFrame) -> str:
    """Returns the polars DataFrame as a markdown table string, with no truncation etc."""
    # Get column names
    columns = table.columns

    # Create header row
    header = "| " + " | ".join(columns) + " |"

    # Create separator row
    separator = "| " + " | ".join(["---" for _ in columns]) + " |"

    # Create data rows - using Polars' row iteration capabilities
    rows = []
    for row in table.iter_rows(named=False):
        formatted_values = []
        for value in row:
            # Convert values to strings with proper handling of None/null values
            if value is None:
                formatted_values.append("")
            else:
                formatted_values.append(str(value))

        rows.append("| " + " | ".join(formatted_values) + " |")

    # Combine all parts
    return "\n".join([header, separator] + rows)


def write_index_markdown(input_files: list[Path | str], output_file: Path | str) -> None:
    """Writes a markdown file with the information about the input files."""
    file_info = _collect_info(input_files)
    output_file = Path(output_file)
    table_markdown = get_table_markdown(file_info)

    result_content = (
        "# File Information\n"
        "\n"
        "This file shows some basic information about the submitted files:"
        "\n"
        f"{table_markdown}"
        "\n"
    )
    output_file.write_text(result_content)

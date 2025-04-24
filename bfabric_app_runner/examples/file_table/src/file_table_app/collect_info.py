from pathlib import Path

import polars as pl
import yaml


def _collect_info(input_files: list[Path | str]) -> pl.DataFrame:
    """Loads the input file contents and returns it as a polars DataFrame."""
    input_files = [Path(f) for f in input_files]
    input_rows = [yaml.safe_load(input_file.read_text()) for input_file in input_files]
    return pl.DataFrame(input_rows)


def _get_table_markdown(table: pl.DataFrame) -> str:
    with pl.Config(tbl_formatting="MARKDOWN"):
        return repr(table)


def write_index_markdown(input_files: list[Path | str], output_file: Path | str) -> None:
    """Writes a markdown file with the information about the input files."""
    file_info = _collect_info(input_files)
    output_file = Path(output_file)
    table_markdown = _get_table_markdown(file_info)

    result_content = (
        "# File Information\n"
        "\n"
        "This file shows some basic information about the submitted files:"
        "\n"
        f"{table_markdown}"
        "\n"
    )
    output_file.write_text(result_content)

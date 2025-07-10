from pathlib import Path

import polars as pl
import yaml


def _collect_info(input_files: list[Path | str]) -> pl.DataFrame:
    """Loads the input file contents and returns it as a polars DataFrame."""
    input_files = [Path(f) for f in input_files]
    input_rows = [yaml.safe_load(input_file.read_text()) for input_file in input_files]
    return pl.DataFrame(input_rows)


def get_table_html(table: pl.DataFrame) -> str:
    """Returns the polars DataFrame as an HTML table string."""
    # Get column names
    columns = table.columns

    # Create header row
    header_cells = "".join(f"<th>{col}</th>" for col in columns)
    header = f"<tr>{header_cells}</tr>"

    # Create data rows
    rows = []
    for row in table.iter_rows(named=False):
        formatted_values = []
        for value in row:
            # Convert values to strings with proper handling of None/null values
            if value is None:
                formatted_values.append("")
            else:
                formatted_values.append(str(value))

        row_cells = "".join(f"<td>{val}</td>" for val in formatted_values)
        rows.append(f"<tr>{row_cells}</tr>")

    # Combine all parts
    tbody_content = "".join(rows)
    return f"<table><thead>{header}</thead><tbody>{tbody_content}</tbody></table>"


def write_index_html(input_files: list[Path | str], output_file: Path | str) -> None:
    """Writes an HTML file with the information about the input files."""
    file_info = _collect_info(input_files)
    output_file = Path(output_file)
    table_html = get_table_html(file_info)

    result_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Information</title>
</head>
<body>
    <section>
        <h1>File Information</h1>
        <p>This file shows some basic information about the submitted files:</p>
        {table_html}
    </section>
</body>
</html>"""

    output_file.write_text(result_content)

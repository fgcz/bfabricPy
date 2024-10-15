#!/usr/bin/env python3
"""
Author:
     Maria d'Errico <maria.derrico@fgcz.ethz.ch>


Description:
 The following script gets a csv file as input and automatically
 generates a json structure with attributes accepted by B-Fabric for
 the creation of datasets.

 Example of input file:
  attr1, attr2
  "1", "1"
  "2", "2"

 Example of json output:
  obj['attribute'] = [ {'name':'attr1', 'position':1},
                       {'name':'attr2', 'position':2} ]
  obj['item'] = [ {'field': [{'value': 1, 'attributeposition':1},
                             {'value': 1,  'attributeposition':2 }],
                   'position':1},
                  {'field': [{'value': 2, 'attributeposition':1},
                          {'value': 2,  'attributeposition':2 }],
                   'position':2}]

Usage: bfabric_save_csv2dataset.py [-h] --csvfile CSVFILE --name NAME --containerid int [--workunitid int]
"""

from pathlib import Path
from typing import Optional, Union

import cyclopts
import polars as pl

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging

app = cyclopts.App()


def polars_to_bfabric_type(dtype: pl.DataType) -> Optional[str]:
    """Returns the B-Fabric type for a given Polars data type, defaulting to String if no correspondence is found."""
    if str(dtype).startswith("Int"):
        return "Integer"
    elif str(dtype).startswith("String"):
        return "String"
    elif str(dtype).startswith("Float"):
        return "Float"
    else:
        return "String"


def polars_to_bfabric_dataset(data: pl.DataFrame) -> dict[str, list[dict[str, Union[int, str, float]]]]:
    """Converts a Polars DataFrame to a B-Fabric dataset representation."""
    attributes = [
        {"name": col, "position": i + 1, "type": polars_to_bfabric_type(data[col].dtype)}
        for i, col in enumerate(data.columns)
    ]
    items = [
        {
            "field": [{"attributeposition": i_field + 1, "value": value} for i_field, value in enumerate(row)],
            "position": i_row + 1,
        }
        for i_row, row in enumerate(data.iter_rows())
    ]
    return {"attribute": attributes, "item": items}


def bfabric_save_csv2dataset(
    client: Bfabric,
    csv_file: Path,
    dataset_name: str,
    container_id: int,
    workunit_id: Optional[int],
    sep: str,
    has_header: bool,
    invalid_characters: str,
) -> None:
    """Creates a dataset in B-Fabric from a csv file."""
    data = pl.read_csv(csv_file, separator=sep, has_header=has_header, infer_schema_length=None)
    check_for_invalid_characters(data=data, invalid_characters=invalid_characters)
    obj = polars_to_bfabric_dataset(data)
    obj["name"] = dataset_name
    obj["containerid"] = container_id
    if workunit_id is not None:
        obj["workunitid"] = workunit_id
    endpoint = "dataset"
    res = client.save(endpoint=endpoint, obj=obj)
    print(res.to_list_dict()[0])


def check_for_invalid_characters(data: pl.DataFrame, invalid_characters: str) -> None:
    """Raises a RuntimeError if any cell in the DataFrame contains an invalid character."""
    if not invalid_characters:
        return
    invalid_columns_df = data.select(pl.col(pl.String).str.contains_any(list(invalid_characters)).any())
    if invalid_columns_df.is_empty():
        return
    invalid_columns = (
        invalid_columns_df.transpose(include_header=True, header_name="column")
        .filter(pl.col("column_0"))["column"]
        .to_list()
    )
    if invalid_columns:
        raise RuntimeError(f"Invalid characters found in columns: {invalid_columns}")


@app.default
def entrypoint(
    csvfile: Path,
    name: str,
    containerid: int,
    workunitid: Optional[int] = None,
    sep: str = ",",
    no_header: bool = True,
    invalid_characters: str = ",\t",
) -> None:
    """Creates a dataset in B-Fabric from a csv file.

    :param csvfile: the path to the csv file to be uploaded as dataset
    :param name: dataset name as a string
    :param containerid: container id
    :param workunitid: workunit id (if should be associated with a workunit)
    :param sep: the separator to use in the csv file e.g. ',' or '\t'
    :param no_header: the csv file has no header
    :param invalid_characters: characters which are not permitted in a cell (set to empty string to deactivate)
    """
    setup_script_logging()
    client = Bfabric.from_config()
    bfabric_save_csv2dataset(
        client=client,
        csv_file=csvfile,
        dataset_name=name,
        container_id=containerid,
        workunit_id=workunitid,
        sep=sep,
        has_header=no_header,
        invalid_characters=invalid_characters,
    )


if __name__ == "__main__":
    app()

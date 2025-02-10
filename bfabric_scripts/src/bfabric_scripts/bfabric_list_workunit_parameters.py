import argparse
import json

import polars as pl
import rich

from bfabric import Bfabric
from bfabric.experimental import MultiQuery
from bfabric.utils.cli_integration import use_client


def bfabric_list_workunit_parameters(client: Bfabric, application_id: int, max_workunits: int, format: str) -> None:
    """Lists the workunit parameters of the provided application.
    :param client: The Bfabric client to use.
    :param application_id: The application ID to list the workunit parameters for.
    :param max_workunits: The maximum number of workunits to fetch.
    :param format: The output format to use.
    """
    workunits_table_full = get_workunits_table_full(application_id, client, max_workunits)
    workunits_table_explode = workunits_table_full.explode("parameter").with_columns(
        parameter_id=pl.col("parameter").struct[1]
    )
    parameter_table_wide = get_parameter_table(client, workunits_table_explode)

    merged_result = workunits_table_full[
        [
            "workunit_id",
            "created",
            "createdby",
            "name",
            "container_id",
            "inputdataset_id",
            "resource_ids",
        ]
    ].join(parameter_table_wide, on="workunit_id", how="left")

    print_results(format, merged_result)


def get_workunits_table_full(application_id: int, client: Bfabric, max_workunits: int) -> pl.DataFrame:
    """Returns a table with the workunits for the specified application."""
    # read the workunit data
    workunits_table_full = (
        client.read("workunit", {"applicationid": application_id}, max_results=max_workunits)
        .to_polars()
        .rename({"id": "workunit_id"})
    )
    # add some extra columns flattening the structure for the output
    workunits_table_full = workunits_table_full.with_columns(
        container_id=pl.col("container").struct[1],
        resource_ids=pl.col("resource").map_elements(
            lambda x: json.dumps([xx["id"] for xx in x]), return_dtype=pl.String
        ),
    )
    if "inputdataset" in workunits_table_full.columns:
        workunits_table_full = workunits_table_full.with_columns(
            inputdataset_id=pl.col("inputdataset").struct[1],
        )
    else:
        workunits_table_full = workunits_table_full.with_columns(inputdataset_id=pl.lit(None))
    return workunits_table_full


def print_results(format: str, merged_result: pl.DataFrame) -> None:
    """Prints the results to the console, in the requested format."""
    if format == "tsv":
        print(merged_result.write_csv(file=None, separator="\t"))
    elif format == "json":
        print(merged_result.write_json(file=None))
    elif format == "pretty":
        # use rich
        rich_table = rich.table.Table()
        for column in merged_result.columns:
            rich_table.add_column(column)
        for row in merged_result.iter_rows():
            rich_table.add_row(*map(str, row))
        console = rich.console.Console()
        console.print(rich_table)
    else:
        raise ValueError("Unsupported format")


def get_parameter_table(client: Bfabric, workunits_table_explode: pl.DataFrame) -> pl.DataFrame:
    """Returns a wide format table for the specified parameters, with the key `workunit_id` indicating the source."""
    # load the parameters table
    collect = MultiQuery(client=client).read_multi(
        endpoint="parameter",
        obj={},
        multi_query_key="id",
        multi_query_vals=workunits_table_explode["parameter_id"].to_list(),
    )
    parameter_table_full = collect.to_polars().rename({"id": "parameter_id"})[["parameter_id", "key", "value"]]
    # add workunit id to parameter table
    parameter_table_full = parameter_table_full.join(
        workunits_table_explode[["workunit_id", "parameter_id"]],
        on="parameter_id",
        how="left",
    )
    # convert to wide format
    return parameter_table_full.pivot(values="value", index="workunit_id", columns="key")


@use_client
def main(*, client: Bfabric) -> None:
    """Parses command line arguments and calls `bfabric_list_workunit_parameters`."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "application_id",
        type=int,
        help="The application ID to list the workunit parameters for.",
    )
    parser.add_argument(
        "--max-workunits",
        type=int,
        help="The maximum number of workunits to fetch.",
        default=200,
    )
    parser.add_argument("--format", choices=["tsv", "json", "pretty"], default="tsv")
    args = vars(parser.parse_args())
    bfabric_list_workunit_parameters(client, **args)


if __name__ == "__main__":
    main()

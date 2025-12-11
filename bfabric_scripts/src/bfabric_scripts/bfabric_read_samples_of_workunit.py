from __future__ import annotations

from bfabric.entities.core.entity import Entity

"""
Copyright (C) 2022 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3


2022-06-03 add sample.name

Usage example:
  bfabric_read_samples_of_workunit.py 278175
"""
import argparse
from typing import TYPE_CHECKING, cast
import polars as pl
from loguru import logger
from bfabric.utils.cli_integration import use_client

from bfabric import Bfabric
from bfabric.entities import Workunit

if TYPE_CHECKING:
    from bfabric.entities.core.uri import EntityUri


def bfabric_read_samples_of_workunit(workunit_id: int, client: Bfabric) -> None:
    """Reads the samples of the specified workunit and prints the results to stdout."""

    workunit = client.reader.read_id("workunit", workunit_id, expected_type=Workunit)
    if workunit is None:
        raise ValueError(f"Workunit {workunit_id} not found")

    collect: list[dict[str, int | str]] = []
    sample_uris = {
        cast("EntityUri | None", input_resource.refs.uris.get("sample")) for input_resource in workunit.input_resources
    }
    logger.debug(f"Querying samples: {sample_uris}")
    sample_uris = {item for item in sample_uris if item is not None}
    samples = client.reader.read_uris(sample_uris)
    samples = {key: value for key, value in samples.items() if value is not None}

    for input_resource in workunit.input_resources:
        input_resource_id = input_resource["id"]
        input_resource_name = input_resource["name"]

        if not isinstance(input_resource_id, int):
            raise ValueError(f"Input resource ID is not an integer: {input_resource_id}")
        if not isinstance(input_resource_name, str):
            raise ValueError(f"Input resource name is not a string: {input_resource_name}")

        data = {
            "workunit_id": workunit_id,
            "inputresource_id": input_resource_id,
            "inputresource_name": input_resource_name,
        }
        sample_uri = input_resource.refs.uris.get("sample")
        if sample_uri is not None:
            if isinstance(sample_uri, list):
                raise ValueError("Should not be a list")
            sample = samples[sample_uri]
            sample_name = sample["name"]
            if not isinstance(sample_name, str):
                raise ValueError(f"Sample name is not a string: {sample_name}")
            data["sample_name"] = sample_name
            data["groupingvar_name"] = _get_sample_groupingvar_name(sample)
        else:
            data["sample_name"] = ""
            data["groupingvar_name"] = "NA"
        collect.append(data)

    table = pl.DataFrame(collect)
    print(table.write_csv(separator="\t"))


def _get_sample_groupingvar_name(sample: Entity) -> str:
    groupingvar = sample["groupingvar"]
    if groupingvar and isinstance(groupingvar, dict):
        name = groupingvar["name"]
        if not isinstance(name, str):
            raise ValueError("groupingvar name should be a string")
        return name
    return "NA"


@use_client
def main(*, client: Bfabric) -> None:
    """Parses the command line arguments and calls `bfabric_read_samples_of_workunit`."""
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("workunit_id", type=int, help="workunit id")
    args = parser.parse_args()
    bfabric_read_samples_of_workunit(workunit_id=cast(int, args.workunit_id), client=client)


if __name__ == "__main__":
    main()

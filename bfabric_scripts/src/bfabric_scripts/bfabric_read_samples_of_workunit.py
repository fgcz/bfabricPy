#!/usr/bin/env python3
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
import polars as pl
from loguru import logger
from bfabric.utils.cli_integration import use_client
from rich.console import Console

from bfabric import Bfabric


def bfabric_read_samples_of_workunit(workunit_id: int, client: Bfabric) -> None:
    """Reads the samples of the specified workunit and prints the results to stdout."""

    workunit = client.reader.read_id("workunit", workunit_id)
    collect = []

    sample_uris = {input_resource.refs.uris.get("sample") for input_resource in workunit.input_resources}
    logger.debug(f"Querying samples: {sample_uris}")
    if None in sample_uris:
        sample_uris.remove(None)
    samples = client.reader.read_uris(sample_uris)

    for input_resource in workunit.input_resources:
        data = {
            "workunit_id": workunit_id,
            "inputresource_id": input_resource["id"],
            "inputresource_name": input_resource["name"],
        }
        sample_uri = input_resource.refs.uris.get("sample")
        if sample_uri is not None:
            sample = samples[sample_uri]
            data["sample_name"] = sample["name"]
            data["sample_groupingvar"] = sample["groupingvar"]["name"] if sample["groupingvar"] else "NA"
        else:
            data["sample_name"] = None
            data["sample_groupingvar"] = "NA"
        collect.append(data)

    table = pl.DataFrame(collect)
    print(table.write_csv(separator="\t"))


@use_client
def main(*, client: Bfabric) -> None:
    """Parses the command line arguments and calls `bfabric_read_samples_of_workunit`."""
    parser = argparse.ArgumentParser()
    parser.add_argument("workunit_id", type=int, help="workunit id")
    args = parser.parse_args()
    bfabric_read_samples_of_workunit(workunit_id=args.workunit_id, client=client)


if __name__ == "__main__":
    main()

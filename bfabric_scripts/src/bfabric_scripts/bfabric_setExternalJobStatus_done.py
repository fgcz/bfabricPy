#!/usr/bin/env python3
"""
set status of a resource of a given resource id
"""

from __future__ import annotations
import argparse

from bfabric import Bfabric


# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#   Maria d'Errico <maria.derrico@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#


def set_external_job_status_done(client: Bfabric, external_job_id: list[int]) -> None:
    """Sets the status of the specified external jobs to 'done'."""
    for job_id in external_job_id:
        try:
            res = client.save("externaljob", {"id": job_id, "status": "done"}).to_list_dict()
            print(res)
        except Exception:
            print(f"failed to set externaljob with id={job_id} 'available'.")
            raise


def main() -> None:
    """Parses command line arguments and calls `set_external_job_status_done`."""
    parser = argparse.ArgumentParser(description="set external job status to 'done'")
    parser.add_argument("external_job_id", type=int, help="external job id", nargs="+")
    args = parser.parse_args()
    client = Bfabric.connect()
    set_external_job_status_done(client, args.external_job_id)


if __name__ == "__main__":
    main()

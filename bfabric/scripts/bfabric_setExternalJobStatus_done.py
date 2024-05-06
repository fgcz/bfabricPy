#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
set status of a resource of a given resource id
"""
import argparse

from bfabric.bfabric2 import Bfabric

# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#   Maria d'Errico <maria.derrico@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_setExternalJobStatus_done.py $
# $Id: bfabric_setExternalJobStatus_done.py 2996 2017-08-18 12:11:17Z cpanse $


def main() -> None:
    parser = argparse.ArgumentParser(description="set external job status to 'done'")
    parser.add_argument("external_job_id", type=int, help="external job id", nargs="+")
    args = parser.parse_args()
    client = Bfabric.from_config(verbose=True)

    for job_id in args.external_job_id:
        try:
            res = client.save("externaljob", {"id": job_id, "status": "done"})
            print(res)
        except Exception:
            print("failed to set externaljob with id={} 'available'.".format(job_id))
            raise


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: latin1 -*-
"""
Copyright (C) 2023 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Lists applications that are not available on bfabric.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under GPL version 3
"""

import sys
from datetime import datetime, timedelta

from bfabric.bfabric2 import default_client


def print_color_msg(msg, color="93"):
    msg = "\033[{color}m--- {} ---\033[0m\n".format(msg, color=color)
    sys.stderr.write(msg)


def render_output(wu):
    wu = list(filter(lambda x: x["createdby"] not in ["gfeeder", "itfeeder"], wu))

    cm = {
        "PENDING": "\033[33mPending   \033[0m",
        "PROCESSING": "\033[34mProcessing\033[0m",
        "FAILED": "\033[31mFailed    \033[0m",
    }

    for x in wu:
        if x["status"] in cm:
            statuscol = cm[x["status"]]
        else:
            statuscol = "\033[36m{} \033[0m".format(x["status"])
        print(
            "A{aid:3} WU{wuid} {cdate} {status} {createdby:12} {name}".format(
                status=statuscol,
                cdate=x["created"],
                wuid=x["id"],
                createdby=x["createdby"],
                name=x["name"],
                aid=x["application"]["id"]
            )
        )

if __name__ == "__main__":
    client = default_client()
    date_cutoff = datetime.today() - timedelta(days=14)

    print_color_msg(
        "list not available proteomics workunits created after {}".format(date_cutoff)
    )

    for status in ["Pending", "Processing", "Failed"]:
        pending_workunits = client.read(
            endpoint="workunit",
            obj={"status": status, "createdafter": date_cutoff},
        ).to_list_dict()

        render_output(pending_workunits)

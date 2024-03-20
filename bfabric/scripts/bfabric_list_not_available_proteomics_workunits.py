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
import bfabric

from datetime import datetime, timedelta

def print_color_msg(msg, color="93"):
    msg = f"\x1b[{color}m--- {msg} ---\x1b[0m\n"
    sys.stderr.write(msg)

def render_output(wu):
    wu = list(filter(lambda x: x.createdby not in  ["gfeeder", "itfeeder"], wu))

    cm = {"PENDING" : "\033[33mPending   \033[0m",
        "PROCESSING": "\033[34mProcessing\033[0m",
        "FAILED"    : "\033[31mFailed    \033[0m"}

    for x in wu:
        if x.status in cm:
            statuscol = cm[x.status]
        else:
            statuscol = f"\x1b[36m{x.status} \x1b[0m"
        print("A{aid:3} WU{wuid} {cdate} {status} {createdby:12} {name}"
               .format(status = statuscol,
                    cdate = x.created,
                    wuid = x._id,
                    createdby = x.createdby,
                    name = x.name,
                    aid = x.application._id))

if __name__ == "__main__":
    B = bfabric.Bfabric()
    d = datetime.today() - timedelta(days=14)

    print_color_msg(f"list not available proteomics workunits created after {d}")

    for status in ['Pending', 'Processing', 'Failed']:
        pwu = B.read_object(endpoint = 'workunit',
                            obj = {'status': status, 'createdafter': d},
                            plain = True,
                            page = 1)
        try:
            render_output(pwu.workunit)
        except:
            pass

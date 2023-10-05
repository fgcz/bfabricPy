#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""

Copyright (C) 2023 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3
"""

import sys
import bfabric

from datetime import datetime, timedelta



def print_color_msg(msg, color="93"):
    msg = "\033[{color}m--- {} ---\033[0m\n".format(msg, color=color)
    sys.stderr.write(msg)


def renderoutput(wu):
    wu = list(filter(lambda x: x.createdby not in  ["gfeeder", "itfeeder"], wu))


    cm = {"Pending" : "\033[33mPending   \033[0m",
        "Processing": "\033[34mProcessing\033[0m",
        "Failed"    : "\033[31mFailed    \033[0m"}

    for x in wu:
        print ("WU{wuid}\t{cdate}\t{status}\t{createdby:12}\t{name}".format(status = cm[s], cdate = x.created, wuid = x._id, createdby = x.createdby, name = x.name))


if __name__ == "__main__":

    B = bfabric.Bfabric()
    d = datetime.today() - timedelta(days=14)

    print_color_msg("list not available proteomics workunits created after {}".format(d))

    for s in ['Pending', 'Processing', 'Failed']:
        pwu = B.read_object(endpoint='workunit', obj={'status': s, 'createdafter': d }, plain = True, page = 1)
        try:
            renderoutput(pwu.workunit)
        except:
            pass

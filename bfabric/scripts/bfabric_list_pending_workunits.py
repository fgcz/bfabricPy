#!/usr/bin/env python
# -*- coding: latin1 -*-

"""

Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_list_pending_workunits.py $
$Id: bfabric_list_pending_workunits.py 3000 2017-08-18 14:18:30Z cpanse $ 

"""

import signal
import sys
from bfabric import Bfabric



def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    bfapp = Bfabric(verbose=True)
    workunit = bfapp.read_object(endpoint='workunit', obj={'status': 'pending'})
    map(lambda x: sys.stdout.write("{0}\t{1}\t{2}\n".format(x._id, x.createdby, x.modified)), workunit)

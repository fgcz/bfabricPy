#!/usr/bin/env python
# -*- coding: latin1 -*-

"""

Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Author:
 Christian Panse <cp@fgcz.ethz.ch>

Licensed under  GPL version 3

$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_create_bfabricrc.py $
$Id: bfabric_create_bfabricrc.py 2475 2016-09-26 09:02:07Z cpanse $ 

"""

import sys
import os



bfabricrc = """
_WEBBASE="http://fgcz-bfabric.uzh.ch/bfabric"
_LOGIN="LOGIN"
_PASSWD='WEPPASSWORD'
SCRATCHSPACE="/export/bfabric/scratch"
DEBUG=1
_DEBUGFILE=/tmp/bfabricdebug.log
_LOGFILE=/tmp/bfabriclog.log

"""

if __name__ == "__main__":
    home = os.path.expanduser("~")
    print "home is '{}'.".format(home)

    bfabricrc_filename = "{}/.bfabricrc.py".format(home)
    if os.path.isfile(bfabricrc_filename):
        print "found '{}'.".format(bfabricrc_filename)
    else:
        print "creating '{}' ...".format(bfabricrc_filename)
        with open(bfabricrc_filename, 'w') as f:
            f.write(bfabricrc)
        print "'{}' file greated. please edit and provide login and password.".format(bfabricrc_filename)

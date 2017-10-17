#!/usr/bin/python
# -*- coding: latin1 -*-

# $Id: bfabric_save_resource.py 2965 2017-08-12 14:09:03Z cpanse $
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_save_resource.py $
# $Date: 2017-08-12 16:09:03 +0200 (Sat, 12 Aug 2017) $


""" 
(xmlResource){
   _id = 406037
   created = 2017-08-11 14:23:25.000798
   createdby = "tobiasko"
   modified = 2017-08-11 14:26:39.000382
   modifiedby = "tobiasko"
   status = "available"
   name = "ProteomeDiscovererQC_2_-_input_resources"
   filechecksum = "2e75672a5d442a8afd2aaac7a49af95a"
   relativepath = "/p2122/bfabric/Proteomics/ProteomeDiscovererQC/2017/2017-08/2017-08-11/workunit_157425/406037.html"
   size = 52671
   project = 
      (xmlProject){
         _id = 2122
      }
   storage = 
      (xmlStorage){
         _id = 2
      }
   uris[] = 
      "http://fgcz-proteomics.uzh.ch/dm//p2122/bfabric/Proteomics/ProteomeDiscovererQC/2017/2017-08/2017-08-11/workunit_157425/406037.html",
      "http://fgcz-proteomics.uzh.ch//p2122/bfabric/Proteomics/ProteomeDiscovererQC/2017/2017-08/2017-08-11/workunit_157425/406037.html",
      "scp://fgcz-proteomics.uzh.ch/srv/www/htdocs//p2122/bfabric/Proteomics/ProteomeDiscovererQC/2017/2017-08/2017-08-11/workunit_157425/406037.html",
   url = "scp://fgcz-proteomics.uzh.ch/srv/www/htdocs//p2122/bfabric/Proteomics/ProteomeDiscovererQC/2017/2017-08/2017-08-11/workunit_157425/406037.html"
   junk = False
   workunit = 
      (xmlWorkunit){
         _id = 157425
      }
 }
"""

import os
import re
import time
import sys
from bfabric import Bfabric

 
################################################################################
if __name__ == "__main__":
    BFABRICSTORAGEID = 2
    bfapp = Bfabric()

    obj = { 'workunitid': 157425,
            'filechecksum': 'ed777890d0edae75830af6829909a07c',
            'relativepath': '/p2122/bfabric/Proteomics/ProteomeDiscovererQC/2017/2017-08/2017-08-11/workunit_157425/R405719_MSMSSpectrumInfo.txt',
            'name': 'R405719_MSMSSpectrumInfo.txt',
            'size': 1347345,
            'status': 'available',
            'storageid': BFABRICSTORAGEID
            }

    res = bfapp.save_object(endpoint='resource', obj=obj)
    print res

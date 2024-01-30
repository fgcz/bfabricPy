#!/usr/bin/python3
# -*- coding: latin1 -*-

"""General Importresource Feeder for bfabric

Author:
    Christian Panse <cp@fgcz.ethz.ch>, 2012-2024

Usage:
    runs under www-data credentials

    $ echo "906acd3541f056e0f6d6073a4e528570;1345834449;46342144;p996/Proteomics/TRIPLETOF_1/jonas_20120820_SILAC_comparison/ 20120824_01_NiKu_1to5_IDA_rep2.wiff" | bfabric_save_importresource_sample.py - 

History:
    The first version of the scrpt appeared on Wed Oct 24 17:02:04 CEST 2012. 
"""



import os
import re
import time
import sys
from bfabric import Bfabric

 
import logging, logging.handlers

logger = logging.getLogger('sync_feeder')
hdlr_syslog = logging.handlers.SysLogHandler(address=("130.60.81.21", 514))
formatter = logging.Formatter('%(name)s %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
hdlr_syslog.setFormatter(formatter)
logger.addHandler(hdlr_syslog)
logger.setLevel(logging.INFO)


################################################################################
bfabric_storageid = 2
bfapp = Bfabric()

# TODO(cp): should go into a config file, e.g., bfabricrc
# the hash  maps the 'real world' to the BFabric application._id
if bfapp.application is None:
    raise RuntimeError("No bfapp.application variable configured. check '~/.bfabricrc.py' file!")
print (bfapp.application)
bfabric_application_ids = bfapp.application

def save_importresource(line):
    """ reads, splits and submit the input line to the bfabric system
    Input: a line containg
    md5sum;date;size;path

    "906acd3541f056e0f6d6073a4e528570;
    1345834449;
    46342144;
    p996/Proteomics/TRIPLETOF_1/jonas_20120820/20120824_01_NiKu_1to5_IDA_rep2.wiff"

    Output:
        True on success otherwise an exception raise
    """

    _bfabric_applicationid = -1
    _bfabric_projectid = -1,
    _file_size = -1
    _file_date = -1

    # empty string / file
    _md5 = "d41d8cd98f00b204e9800998ecf8427e"

    _sampleid = None

    try:
        (_md5,  _file_date, _file_size, _file_path) = line.split(";")
    except:
        raise



    # the timeformat bfabric understands
    #_file_date = time.strftime("%FT%H:%M:%S-01:00",time.gmtime(int(_file_date)))
    _file_date = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(int(_file_date)))

    # linear search through dictionary. first hit counts!
    for i in bfabric_application_ids.keys():
        # first match counts!
        if re.search(i, _file_path):
            _bfabric_applicationid = bfabric_application_ids[i]
            re_result = re.search(r"^p([0-9]+)\/.+", _file_path)
            _bfabric_projectid = re_result.group(1)
            break

    if _bfabric_applicationid < 0:
        logger.error("{0}; no bfabric application id.".format(_file_path))
        return 

    obj = { 'applicationid':_bfabric_applicationid,
            'filechecksum':_md5,
            'containerid':_bfabric_projectid,
            'filedate':_file_date,
            'relativepath':_file_path,
            'name': os.path.basename(_file_path),
            'size':_file_size,
            'storageid': bfabric_storageid
            }

    try:
        m = re.search(r"p([0-9]+)\/(Proteomics\/[A-Z]+_[1-9])\/.*_\d\d\d_S([0-9][0-9][0-9][0-9][0-9][0-9]+)_.*(raw|zip)$", _file_path)
        print ("found sampleid={} pattern".format(m.group(3)))
        obj['sampleid'] = int(m.group(3))
    except:
        pass


    print (obj)
    res = bfapp.save_object(endpoint='importresource', obj=obj)
    print (res[0])

if __name__ == "__main__":
    if sys.argv[1] == '-':
        print ("reading from stdin ...")
        for input_line in sys.stdin:
            save_importresource(input_line.rstrip())
    elif sys.argv[1] == '-h':
        print(__doc__)
    else:
        save_importresource(sys.argv[1])


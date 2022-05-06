#!/usr/bin/env python3
# -*- coding: latin1 -*-

# $Id: bfabric_save_importresource.py 2526 2016-10-17 10:25:25Z cpanse $
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_save_importresource.py $
# $Date: 2016-10-17 12:25:25 +0200 (Mon, 17 Oct 2016) $


""" Gerneral Importresource Feeder for bfabric

author: Christian Panse <cp@fgcz.ethz.ch>

usage:

$ ./prg "906acd3541f056e0f6d6073a4e528570;1345834449;46342144;\
p996/Proteomics/TRIPLETOF_1/jonas_20120820_SILAC_comparison/\
20120824_01_NiKu_1to5_IDA_rep2.wiff"

or reading from stdin

$ echo "906acd3541f056e0f6d6073a4e528570;\
1345834449;\
46342144;\
p996/Proteomics/TRIPLETOF_1/jonas_20120820_SILAC_comparison/\
20120824_01_NiKu_1to5_IDA_rep2.wiff" | ./prg - 

template
https://fgcz-bfabric.uzh.ch/bfabric/importresource?wsdl
"""


# Wed Oct 24 17:02:04 CEST 2012 Christian Panse <cp@fgcz.ethz.ch>; 
# refactoring from Marcos bash code
# Thu Oct 25 09:04:09 CEST 2012 Christian Panse <cp@fgcz.ethz.ch>;  testing
# Thu Nov 13 22:03:01 CET 2014 refactor using pylint bfabric8 w
# Mon Mar  2 12:23:54 CET 2015 added syslog handler
# Wed Oct 25 11:21:41 CEST 2017 refactor and bfabric9 testing

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
bfabric_application_ids = {'Proteomics/TOFTOF_2':91,
    'Proteomics/T100_1':18, 
    'Proteomics/TRIPLETOF_1':93,
    'Proteomics/VELOS_1':90, 
    'Proteomics/VELOS_2':89,
    'Proteomics/ORBI_1':10, 
    'Proteomics/ORBI_2':12,
    'Proteomics/ORBI_3':87, 
    'Proteomics/G2HD_1':128,
    'Proteomics/G2HD_2':251,
    'Proteomics/LTQ_1':7, 
    'Proteomics/LTQFT_1':8,
    'Proteomics/QTRAP_1':92, 
    'Proteomics/TSQ_1':15,
    'Proteomics/TSQ_2':53, 
    'Proteomics/Analysis/Progenesis':84, 
    'Proteomics/Analysis/ProteinPilot':148,
    'Proteomics/Analysis/MaxQuant':151,
                           'Proteomics/Analysis/FragPipeGuiZip':299,
                           'Proteomics/Analysis/GenericZip':185,
                           'Proteomics/QEXACTIVE_1':160,
                           'Proteomics/QEXACTIVE_2':161,
                           'Proteomics/QEXACTIVE_3':163,
                           'Proteomics/FUSION_1':162,
                           'Proteomics/FUSION_2':176,
                           'Proteomics/LUMOS_1':248,
                           'Proteomics/QEXACTIVEHF_1':177,
                           'Proteomics/QEXACTIVEHF_2':197,
                           'Proteomics/QEXACTIVEHF_3':207,
                           'Proteomics/QEXACTIVEHF_4':254,
                           'Proteomics/LUMOS_2':268,
                           'Proteomics/EXPLORIS_1':269,
                           'Proteomics/EXPLORIS_2':301,
                           'Proteomics/PROTEONXPR36': 82,
                           'Proteomics/EXTERNAL_0': 188,
                           'Proteomics/EXTERNAL_1': 189,
                           'Proteomics/EXTERNAL_2': 190,
                           'Proteomics/EXTERNAL_3': 191,
                           'Proteomics/EXTERNAL_4': 192,
                           'Proteomics/EXTERNAL_5': 193,
                           'Proteomics/QEXACTIVEHFX_1': 232,
                           'Proteomics/TIMSTOF_1': 243,
                           'Proteomics/QDA_1': 271,
                           'Proteomics/G2SI_2': 272,
                           'Proteomics/QUANTIVA_1': 284,
                           'Metabolomics/G2SI_1':250,
                           'Metabolomics/QEXACTIVE_3':171,
                           'Metabolomics/TRIPLETOF_1':144,
                           'Metabolomics/TOFTOF_2':143,
                           'Metabolomics/QTOF':14,
                           'Metabolomics/LTQFT_1':9,
                           'Metabolomics/G2HD_1':81,
                           'Metabolomics/TSQ_1':16,
                           'Metabolomics/TSQ_2':43,
                           'Metabolomics/GCT_1':44,
                           'Metabolomics/ORBI_1':11,
                           'Metabolomics/ORBI_2':13,
                           'Metabolomics/IMSTOF_1':203,
                           'Metabolomics/QUANTIVA_1':214,
                           'Metabolomics/Analysis/ProgenesisQI':226,
                           'Metabolomics/ORBI_3':77}

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
        m = re.search(r"p([0-9]+)\/(Proteomics\/[A-Z]+_[1-9])\/.*_S([0-9][0-9][0-9][0-9][0-9][0-9]+)_.*raw$", _file_path)
        print ("found sampleid={} pattern".format(m.group(3)))
        obj['sampleid'] = int(m.group(3))
    except:
        pass


    print (obj)
    #return
    res = bfapp.save_object(endpoint='importresource', obj=obj)
    print (res[0])

if __name__ == "__main__":
    if sys.argv[1] == '-':
        print ("reading from stdin ...")
        for input_line in sys.stdin:
            save_importresource(input_line.rstrip())
    else:
        save_importresource(sys.argv[1])


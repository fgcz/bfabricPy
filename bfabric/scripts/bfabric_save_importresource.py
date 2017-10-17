#!/usr/bin/python
# -*- coding: latin1 -*-

# $Id: bfabric_save_importresource.py 2526 2016-10-17 10:25:25Z cpanse $
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_save_importresource.py $
# $Date: 2016-10-17 12:25:25 +0200 (Mon, 17 Oct 2016) $


""" Gerneral Importresource Feeder for B-Fabric

replacement for 
http://fgcz-svn.uzh.ch/viewvc/fgcz/stable/bfabric/admin/\
bin/NewDesign/prxir_compact.sh

AUTHOR:
Christian Panse <cp@fgcz.ethz.ch>

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

this is what you get when you connect to 
https://fgcz-bfabric.uzh.ch/bfabric/importresource?wsdl

SAMPLE_QUERY = '''
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
xmlns:end="http://endpoint.webservice.component.bfabric.org/">
   <soapenv:Header/>
   <soapenv:Body>    
      <end:save>
         <parameters>
            <login>?</login>
            <password>?</password>
            <!--Zero or more repetitions:-->
            <importresource>
               <!--Optional:-->
               <id>?</id>
               <!--Optional:-->
               <name>?</name>
               <!--Optional:-->
               <applicationid>?</applicationid>
               <!--Optional:-->
               <description>?</description>
               <!--Optional:-->
               <expirationdate>?</expirationdate>
               <!--Optional:-->
               <filechecksum>?</filechecksum>
               <!--Optional:-->
               <filedate>?</filedate>
               <!--Optional:-->
               <projectid>?</projectid>
               <!--Optional:-->
               <relativepath>?</relativepath>
               <!--Optional:-->
               <size>?</size>
               <!--Optional:-->
               <storageid>?</storageid>
               <!--Optional:-->
               <url>?</url>
               <!--Optional:-->
               <weburl>?</weburl>
            </importresource>
         </parameters>
      </end:save>
   </soapenv:Body>
</soapenv:Envelope>
'''


"""


# Wed Oct 24 17:02:04 CEST 2012 Christian Panse <cp@fgcz.ethz.ch>; 
# refactoring from Marcos bash code
# Thu Oct 25 09:04:09 CEST 2012 Christian Panse <cp@fgcz.ethz.ch>; testing
# Thu Nov 13 22:03:01 CET 2014 refactor using pylint
# Mon Mar  2 12:23:54 CET 2015 added syslog handler

import os
import re
import time
import sys
from bfabric import Bfabric

 
import logging, logging.handlers

logger = logging.getLogger('sync_feeder')
hdlr_syslog = logging.handlers.SysLogHandler(address=("130.60.81.148", 514))
formatter = logging.Formatter('%(name)s %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
hdlr_syslog.setFormatter(formatter)
logger.addHandler(hdlr_syslog)
logger.setLevel(logging.INFO)


################################################################################
BFABRICSTORAGEID = 2
bfapp = Bfabric()

# the hash  maps the 'real world' to the BFabric application._id
APPIDS = {'Proteomics/TOFTOF_2':91, 
    'Proteomics/T100_1':18, 
    'Proteomics/TRIPLETOF_1':93,
    'Proteomics/VELOS_1':90, 
    'Proteomics/VELOS_2':89,
    'Proteomics/ORBI_1':10, 
    'Proteomics/ORBI_2':12,
    'Proteomics/ORBI_3':87, 
    'Proteomics/G2HD_1':128,
    'Proteomics/LTQ_1':7, 
    'Proteomics/LTQFT_1':8,
    'Proteomics/QTRAP_1':92, 
    'Proteomics/TSQ_1':15,
    'Proteomics/TSQ_2':53, 
    'Proteomics/Analysis/Progenesis':84, 
    'Proteomics/Analysis/ProteinPilot':148,
    'Proteomics/Analysis/MaxQuant':151,
    'Proteomics/Analysis/GenericZip':185,
    'Proteomics/QEXACTIVE_1':160,
    'Proteomics/QEXACTIVE_2':161,
    'Proteomics/QEXACTIVE_3':163,
    'Proteomics/FUSION_1':162,
    'Proteomics/FUSION_2':176,
    'Proteomics/QEXACTIVEHF_1':177,
    'Proteomics/QEXACTIVEHF_2':197,
    'Proteomics/QEXACTIVEHF_3':207,
    'Proteomics/PROTEONXPR36': 82,
    'Proteomics/EXTERNAL_0': 188,
    'Proteomics/EXTERNAL_1': 189,
    'Proteomics/EXTERNAL_2': 190,
    'Proteomics/EXTERNAL_3': 191,
    'Proteomics/EXTERNAL_4': 192,
    'Proteomics/EXTERNAL_5': 193,
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
    my_storageid = BFABRICSTORAGEID

    my_applicationid = -1
    my_projectid = -1,
    my_size = -1
    my_filedate = -1

    # empty string / file
    my_filechecksum = "d41d8cd98f00b204e9800998ecf8427e"

    input_array = line.split(";")

    my_filechecksum = input_array[0]

    # the timeformat bfabric understands
    my_filedate = time.strftime("%FT%H:%M:%S-01:00", 
        time.gmtime(int(input_array[1])))

    my_size = input_array[2]
    my_relativepath = input_array[3]

    # linear search through dictionary. first hit counts!
    for i in APPIDS.keys():
        # first match counts!
        if re.search(i, my_relativepath):
            my_applicationid = APPIDS[i]
            re_result = re.search(r"^p([0-9]+)\/.+", my_relativepath)
            my_projectid = re_result.group(1)
            break

    if my_applicationid < 0:
        logger.error("{0}; no APPID.".format(my_relativepath))
        sys.exit(1)

    obj = { 'applicationid':my_applicationid,
            'filechecksum':my_filechecksum,
            'projectid':my_projectid,
            'filedate':my_filedate,
            'relativepath':my_relativepath,
            'name':os.path.basename(my_relativepath),
            'size':my_size,
            'storageid':my_storageid
            }

    res = bfapp.save_object(endpoint='importresource', obj=obj)
    print res

if __name__ == "__main__":
    if sys.argv[1] == '-':
        print "reading from stdin ..."
        for input_line in sys.stdin:
            save_importresource(input_line.rstrip())
    else:
        save_importresource(sys.argv[1])


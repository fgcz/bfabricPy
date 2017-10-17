#!/usr/bin/python
# -*- coding: latin1 -*-

# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_save_mascot_as_importresource.py $
# $Id: bfabric_save_mascot_as_importresource.py 2529 2016-10-17 12:32:20Z cpanse $
# $Date: 2016-10-17 14:32:20 +0200 (Mon, 17 Oct 2016) $


# Mascot Feeder
# 2012-10-08 Christian Panse <cp@fgcz.ethz.ch>
# 2012-10-10 Christian Panse <cp@fgcz.ethz.ch>
# 2012-10-11 Christian Panse <cp@fgcz.ethz.ch>

import os
import signal
import re
import sys
import itertools
import multiprocessing
import urllib 
import hashlib 
import time
import getopt
from bfabric import Bfabric

import logging, logging.handlers
 

logger = logging.getLogger('mascot_feeder')
hdlr_syslog = logging.handlers.SysLogHandler(address=('130.60.81.148', 514))
formatter = logging.Formatter('%(name)s %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
hdlr_syslog.setFormatter(formatter)
logger.addHandler(hdlr_syslog)
logger.setLevel(logging.INFO)


bfapp = Bfabric()
nCPU = 8
svnstring = "$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/bfabric_save_mascot_as_importresource.py $"

def signal_handler(signal, frame):
    print( ( "sys exit 1; signal=" + str(signal)+ "; frame="+str(frame)) )
    sys.exit(1) 

def walkOnError(e):
    print(e)
    sys.exit(1)

def crawlForFiles(path, pattern, mintimediff):
    allPaths = list()
    regex=re.compile(pattern)

    for root, dirs, files in os.walk(path, topdown=True, onerror=walkOnError, followlinks=False):
        for f in files:
            jfile=os.path.join(root,f)
            if regex.match(jfile):
                timediff=time.time() - os.path.getmtime(jfile)
                print (jfile, timediff, timediff/(24*3600))
                if (timediff < mintimediff):
                    allPaths.append(jfile)

    return allPaths


def extractMetaDataPrint(p):
    print (p)
    pass

def feedMascot2BFabric(f):
    regex2=re.compile(".*.+\/(data\/.+\.dat$)")
    regex2Result=regex2.match(f)
    if regex2Result:
        obj = parseMascotDatFile(f)
        if len(obj['inputresource']) > 0:
            res = bfapp.save_object(endpoint='workunit', obj=obj)
            return res

""" 
parse the mascot dat file and extract meta data and title information for inputresource retrival 
it returns a 'workunit' dict for the following web api

<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:end="http://endpoint.webservice.component.bfabric.org/">
   <soapenv:Header/>
   <soapenv:Body>
      <end:checkandinsert>
         <parameters>
            <login>?</login>
            <password>?</password>
            <!--Zero or more repetitions:-->
            <workunit>
               <!--Optional:-->
               <applicationid>?</applicationid>
               <!--Optional:-->
               <projectid>?</projectid>
               <!--Optional:-->
               <name>?</name>
               <!--Optional:-->
               <description>?</description>
               <!--Zero or more repetitions:-->
               <inputresource>
                  <!--Optional:-->
                  <storageid>?</storageid>
                  <!--Optional:-->
                  <relativepath>?</relativepath>
               </inputresource>
               <!--Zero or more repetitions:-->
               <resource>
                  <!--Optional:-->
                  <name>?</name>
                  <!--Optional:-->
                  <storageid>?</storageid>
                  <!--Optional:-->
                  <relativepath>?</relativepath>
                  <!--Optional:-->
                  <weburl>?</weburl>
                  <!--Optional:-->
                  <size>?</size>
                  <!--Optional:-->
                  <filechecksum>?</filechecksum>
               </resource>
            </workunit>
         </parameters>
      </end:checkandinsert>
   </soapenv:Body>
</soapenv:Envelope>
"""
def parseMascotDatFile(f):
    regex0 = re.compile("^title=.*(p([0-9]+).+Proteomics.*(raw|RAW|wiff)).*")
    regex3 = re.compile("^(FILE|COM|release|USERNAME|USERID|TOL|TOLU|ITOL|ITOLU|MODS|IT_MODS|CHARGE|INSTRUMENT|QUANTITATION|DECOY)=(.+)$")
    lineCount = 0
    metaDataDict=dict(COM='', FILE='', release='', relativepath=f.replace('/usr/local/mascot/',''))
    inputresourceHitHash = dict()
    inputresourceList = list()
    md5 = hashlib.md5()
    project = -1
    desc = ""
    with open(f) as myfile:
        for line in myfile:
            lineCount = lineCount + 1
            md5.update(line)
            # check if the first character of the line is a 't' to save regex time
            if line[0] == 't':
                result=regex0.match(urllib.url2pathname(line.strip()).replace('\\',"/").replace("//","/"))
                if result and not inputresourceHitHash.has_key(result.group(1)):
                    inputresourceHitHash[result.group(1)] = result.group(2)
                    inputresourceList.append(dict(storageid=2, relativepath=result.group(1)))
                    project=result.group(2)
                else:
                    # nothing as do be done since the inputresource is already recorded
                    pass
            elif lineCount < 600:
                # none of the regex3 pattern is starting with 't'
                result=regex3.match(urllib.url2pathname(line.strip()))
                if result:
                    desc = desc + result.group(1) + "=" + result.group(2) + "; "
                    metaDataDict[result.group(1)] = result.group(2)

    return (dict(
        applicationid=19,
        projectid=project, 
        name=(metaDataDict['COM'] + "; " + os.path.basename(metaDataDict['relativepath']) + "; " + metaDataDict['FILE'])[:255],
        description=format("{} / {}".format(desc, svnstring),
        inputresource=inputresourceList,
        resource=dict(
            name=metaDataDict['relativepath'],
            storageid=4,
            relativepath=metaDataDict['relativepath'],
            #weburl="scp://fgcz-c-064.fgcz-net.unizh.ch/usr/local/mascot/"+metaDataDict['relativepath'],
            size=os.path.getsize(f),
            filechecksum=md5.hexdigest()
            )
        )
    )

if __name__ == "__main__":
    timdiff=3600*24
    try:
        opts, args = getopt.getopt(sys.argv[1:], "td", ["days=", "mintimediff=", "file="])
    except getopt.GetoptError as err:
        print (str(err))
        sys.exit(2)

    for o, value in opts:
        if o == "--days" or o == "mintimediff":
            if value > 0:
                timediff = 3600 * 24 *  int(value)
            else:
                print ("value not valid")
        elif o == "--file":
            print ("processesing", value, "...")
            feedMascot2BFabric(value)
            sys.exit(0)
            


    # L=crawlForFiles('/usr/local/mascot/data', '.+2012[0-9]+/F174054.dat$', timediff)
    # L=crawlForFiles('/usr/local/mascot/data', '.+2012[0-9]+/F174047.dat$', timediff)
    logger.info("crawlForFiles")
    L=crawlForFiles('/usr/local/mascot/data', '.+data\/20[0-9][0-9][0-9]+\/F[0-9]+\.dat$', timediff)

    logger.info("found {0} mascot canditate mascot files".format(len(L)))

    logger.info("filter files using {0} cpu(s)".format(nCPU))
    pool=multiprocessing.Pool(processes=nCPU)
    L=pool.map(feedMascot2BFabric, L)

    logger.info("done {0} ".format(len(L)))
    print L


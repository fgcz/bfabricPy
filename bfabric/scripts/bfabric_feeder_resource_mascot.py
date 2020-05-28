#!/usr/bin/python
# -*- coding: latin1 -*-

# $HeadURL: http://fgcz-svn.uzh.ch/repos/fgcz/computer/fgcz-s-018/bfabric-feeder/fgcz_dataFeederMascot.py $
# $Id: fgcz_dataFeederMascot.py 8105 2016-11-24 15:31:03Z cpanse $
# $Date: 2016-11-24 16:31:03 +0100 (Thu, 24 Nov 2016) $


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
import urllib.request, urllib.parse, urllib.error 
import hashlib 
import time
import getopt
from suds.client import Client
import logging, logging.handlers

import http.client
http.client.HTTPConnection._http_vsn = 10
http.client.HTTPConnection._http_vsn_str = 'HTTP/1.0'
 
#handler = logging.StreamHandler(sys.stderr)

logger = logging.getLogger('mascot_feeder')
hdlr_syslog = logging.handlers.SysLogHandler(address=('130.60.193.21', 514))
formatter = logging.Formatter('%(name)s %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
hdlr_syslog.setFormatter(formatter)
logger.addHandler(hdlr_syslog)
logger.setLevel(logging.INFO)


SVN="feeder = http://fgcz-svn.uzh.ch/repos/fgcz/computer/fgcz-c-064/bfabric-feeder/fgcz_dataFeederMascot.py"
workuniturl='http://fgcz-bfabric.uzh.ch/bfabric/workunit?wsdl'
# workuniturl='https://fgcz-bfabric-test.uzh.ch/bfabric/workunit?wsdl'
nCPU=8
BFLOGIN='pfeeder'
BFPASSWORD='!ForYourEyesOnly!'

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
                print((jfile, timediff, timediff/(24*3600)))
                if (timediff < mintimediff):
                    allPaths.append(jfile)

    return allPaths

def read_bfabricrc():
    with open(os.environ['HOME']+"/.bfabricrc") as myfile: 
        for line in myfile:
            return(line.strip())

        

def extractMetaDataPrint(p):
    print (p)
    pass

def feedMascot2BFabric(f):
    regex2=re.compile(".*.+\/(data\/.+\.dat$)")
    regex2Result=regex2.match(f)
    if regex2Result:
        wu=parseMascotDatFile(f)
        if len(wu['inputresource']) > 0:
            # "submit to B-Fabric"
            clientWorkUnit=Client(workuniturl)
            try:
                resultClientWorkUnit=clientWorkUnit.service.checkandinsert(dict(
                    login=BFLOGIN, 
                    password=BFPASSWORD, 
                    workunit=wu))
                print (resultClientWorkUnit)
            except Exception as e:
                logger.warning(e)
                return(wu)
        return

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
                result=regex0.match(urllib.request.url2pathname(line.strip()).replace('\\',"/").replace("//","/"))
                if result and result.group(1) not in inputresourceHitHash:
                    inputresourceHitHash[result.group(1)] = result.group(2)
                    inputresourceList.append(dict(storageid=2, relativepath=result.group(1)))
                    project=result.group(2)
                else:
                    # nothing as do be done since the inputresource is already recorded
                    pass
            elif lineCount < 600:
                # none of the regex3 pattern is starting with 't'
                result=regex3.match(urllib.request.url2pathname(line.strip()))
                if result:
                    desc = desc + result.group(1) + "=" + result.group(2) + "; "
                    metaDataDict[result.group(1)] = result.group(2)


    desc = desc.encode('ascii',errors='ignore')
    return (dict(
        applicationid=19,
        projectid=project, 
        name=(metaDataDict['COM'] + "; " + os.path.basename(metaDataDict['relativepath']) + "; " + metaDataDict['FILE'])[:255],
        description=desc+SVN,
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
    BFPASSWORD=read_bfabricrc()
    timdiff=3600*24
    try:
        opts, args = getopt.getopt(sys.argv[1:], "td", ["days=", "mintimediff=", "file="])
    except getopt.GetoptError as err:
        print((str(err)))
        sys.exit(2)

    for o, value in opts:
        if o == "--days" or o == "mintimediff":
            if value > 0:
                timediff = 3600 * 24 *  int(value)
            else:
                print ("value not valid")
        elif o == "--file":
            print(("processesing", value, "..."))
            feedMascot2BFabric(value)
            sys.exit(0)
            


    # L=crawlForFiles('/usr/local/mascot/data', '.+2012[0-9]+/F174054.dat$', timediff)
    # L=crawlForFiles('/usr/local/mascot/data', '.+2012[0-9]+/F174047.dat$', timediff)
    logger.info("crawlForFiles")
    L=crawlForFiles('/usr/local/mascot/data', '.+data\/20[0-9][0-9][0-9]+\/F[0-9]+\.dat$', timediff)

    logger.info("found {0} mascot canditate mascot files".format(len(L)))

    # simon 20140714 there were problems with the multiprocessing method. Therefore switched to snail processing
    #for d in L:
    #	feedMascot2BFabric(d)
    
    logger.info("filter files using {0} cpu(s)".format(nCPU))
    pool=multiprocessing.Pool(processes=nCPU)
    L=pool.map(feedMascot2BFabric, L)

    logger.info("done {0} ".format(len(L)))
    print(L)

    #pool.map_async(extractMetaData, L, callback=extractMetaDataPrint)
    #pool.join()
    #pool.close()

# TODO
# think about using async

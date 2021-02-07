#!/usr/bin/python
# -*- coding: latin1 -*-

# $HeadURL: https://fgcz-svn.uzh.ch/repos/fgcz/computer/fgcz-s-018/bfabric-feeder/fgcz_dataFeederMascot.py $
# $Id: fgcz_dataFeederMascot.py 9097 2021-02-05 15:38:38Z cpanse $
# $Date: 2021-02-05 16:38:38 +0100 (Fri, 05 Feb 2021) $


# Mascot Feeder
# 2012-10-08 Christian Panse <cp@fgcz.ethz.ch>
# 2012-10-10 Christian Panse <cp@fgcz.ethz.ch>
# 2012-10-11 Christian Panse <cp@fgcz.ethz.ch>

import os
import signal
import re
import sys
import itertools
import urllib 
import hashlib 
import time
import getopt
from suds.client import Client
import logging, logging.handlers
import json

import httplib
httplib.HTTPConnection._http_vsn = 10
httplib.HTTPConnection._http_vsn_str = 'HTTP/1.0'


 
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

DB=dict()
try:
    DB = json.load(open("/home/cpanse/mascot.json"))
except:
    pass

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
        if f in DB:
            print ("HITHITHIT")
            wu = DB[f]
        else:
            wu = parseMascotDatFile(f)
            DB[f] = wu

        print("INPUT")
        print (wu)
        if len(wu['inputresource']) > 0:
            if re.search("autoQC4L", wu['name']) or re.search("autoQC01", wu['name']):
                print ("WARNING This script ignores autoQC based mascot dat file {}.".format(f))
                return 

            # "submit to B-Fabric"
            clientWorkUnit=Client(workuniturl)
            try:
                resultClientWorkUnit=clientWorkUnit.service.checkandinsert(dict(
                    login=BFLOGIN, 
                    password=BFPASSWORD, 
                    workunit=wu))
                print("OUTPUT")
                print (resultClientWorkUnit)
            except Exception, e:
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

    control_chars = ''.join(map(unichr, range(0x00,0x20) + range(0x7f,0xa0)))
    control_char_re = re.compile('[%s]' % re.escape(control_chars))

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


    desc = desc.encode('ascii',errors='ignore')

    # name=(metaDataDict['COM'] + "; " + os.path.basename(metaDataDict['relativepath']) + "; " + metaDataDict['FILE'])[:255],
    name = "{}; {}".format(metaDataDict['COM'], os.path.basename(metaDataDict['relativepath']))[:255]

    rv = dict(
        applicationid=19,
        containerid=project, 
        name=control_char_re.sub('', name),
        description=control_char_re.sub('', desc+SVN),
        inputresource=inputresourceList,
        resource=dict(
            name=metaDataDict['relativepath'],
            storageid=4,
            status='available',
            relativepath=metaDataDict['relativepath'],
            size=os.path.getsize(f),
            filechecksum=md5.hexdigest()
            )
        )
    return (rv)

if __name__ == "__main__":
    BFPASSWORD=read_bfabricrc()
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
            json.dump(DB, open("/home/cpanse/mascot.json", 'w'))
            sys.exit(0)
            


    logger.info("crawlForFiles")
    L=crawlForFiles('/usr/local/mascot/data', '.+data\/20[2-9][0-9][0-9]+\/F[0-9]+\.dat$', timediff)

    logger.info("found {0} mascot canditate mascot files".format(len(L)))

    logger.info("filter files using {0} cpu(s)".format(nCPU))
    for f in L:
        feedMascot2BFabric(f)
        print(len(DB))

    logger.info("done {0} ".format(len(L)))

    json.dump(DB, open("/home/cpanse/mascot.json", 'w'))


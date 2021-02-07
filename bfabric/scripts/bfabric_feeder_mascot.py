#!/usr/bin/python
# -*- coding: latin1 -*-
 
"""
# $HeadURL: https://fgcz-svn.uzh.ch/repos/fgcz/computer/fgcz-s-018/bfabric-feeder/fgcz_dataFeederMascot.py $
# $Id: fgcz_dataFeederMascot.py 9097 2021-02-05 15:38:38Z cpanse $
# $Date: 2021-02-05 16:38:38 +0100 (Fri, 05 Feb 2021) $


# LOG
2012-10-08 Christian Panse <cp@fgcz.ethz.ch>
2012-10-10 Christian Panse <cp@fgcz.ethz.ch>
2012-10-11 Christian Panse <cp@fgcz.ethz.ch>
2021-01-06 Christian Panse <cp@fgcz.ethz.ch> - replace multiprocess by caching strategy

# use shell for getting the files ready 

find /usr/local/mascot/data/ -type f -mtime -1 -name "*dat" \
  | /home/cpanse/__checkouts/bfabricPy/bfabric/scripts/bfabric_feeder_mascot.py --stdin

# crontab
0   0      *       *       7       nice -19 /usr/local/fgcz-s-018/bfabric-feeder/run_fgcz_dataFeederMascot.bash 365 2>&1 >/dev/null
3   */2       *       *       1-6       nice -19 /usr/local/fgcz-s-018/bfabric-feeder/run_fgcz_dataFeederMascot.bash 7 2>&1 >/dev/null
*/7   5-22       *       *       1-5     nice -19  /usr/local/fgcz-s-018/bfabric-feeder/run_fgcz_dataFeederMascot.bash 1  2>&1 >/dev/null

"""

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
#import logging, logging.handlers
import json

import httplib
httplib.HTTPConnection._http_vsn = 10
httplib.HTTPConnection._http_vsn_str = 'HTTP/1.0'

#handler = logging.StreamHandler(sys.stderr)

workuniturl='http://fgcz-bfabric.uzh.ch/bfabric/workunit?wsdl'
clientWorkUnit=Client(workuniturl)
BFLOGIN='pfeeder'
BFPASSWORD='!ForYourEyesOnly!'

DB=dict()
DBfilename="{}/mascot.json".format(os.getenv("HOME"))
DBwritten=False
try:
    DB = json.load(open(DBfilename))
except:
    pass

def signal_handler(signal, frame):
    print( ( "sys exit 1; signal=" + str(signal)+ "; frame="+str(frame)) )
    sys.exit(1) 

def read_bfabricrc():
    with open(os.environ['HOME']+"/.bfabricrc") as myfile: 
        for line in myfile:
            return(line.strip())

def feedMascot2BFabric(f):
    regex2=re.compile(".*.+\/(data\/.+\.dat$)")
    regex2Result=regex2.match(f)
    if regex2Result:
        print("input>")
        print ("\t{}".format(f))
        if f in DB:
            print ("\thit")
            wu = DB[f]
            if 'workunitid' in wu:
                print ("\tdat file {} already as workunit id {}".format(f, wu['workunitid']))
                return
            else:
                print ('\tno workunitid found')
        else:
            print ("parsing mascot result file '{}'...".format(f))
            wu = parseMascotDatFile(f)
            DB[f] = wu

        if len(wu['inputresource']) > 0:
            if re.search("autoQC4L", wu['name']) or re.search("autoQC01", wu['name']):
                print ("WARNING This script ignores autoQC based mascot dat file {}.".format(f))
                return 

            print("\tquerying  bfabric ...")
            if 'errorreport' in wu:
                del(wu['errorreport'])

            try:
                resultClientWorkUnit=clientWorkUnit.service.checkandinsert(dict(login=BFLOGIN, password=BFPASSWORD, workunit=wu))
            except Exception, e:
                print("Exception {}".format(e))
                raise

            try:
                rv = resultClientWorkUnit.workunit[0]
            except Exception, e:
                print("Exception {}".format(e))
                raise
                

            print("output>")
            if 'errorreport' in rv:
                print ("\tfound errorreport '{}'.".format(rv['errorreport']))
                DB[f] = wu
                DBwritten=True

            if '_id' in rv:
                wu['workunitid'] = rv['_id']
                print ("\tfound workunitid'{}'.".format(wu['workunitid']))
                DB[f] = wu
                DBwritten=True

            if not '_id' in rv and not 'errorreport' in rv:
                raise
                # print (resultClientWorkUnit)
                #print ("exception for file {} with error {}".format(f, e))
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


    desc = desc.encode('ascii', errors='ignore')

    name = "{}; {}".format(metaDataDict['COM'], os.path.basename(metaDataDict['relativepath']))[:255]

    rv = dict(
        applicationid=19,
        containerid=project, 
        name=control_char_re.sub('', name),
        description=control_char_re.sub('', desc),
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
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f", ["file=", "stdin"])
    except getopt.GetoptError as err:
        print (str(err))
        sys.exit(2)

    for o, value in opts:
        if o == "--stdin":
            print ("reading file names from stdin ...")
            for f in sys.stdin.readlines():
                feedMascot2BFabric(f.strip())
        elif o == "--file" or o == 'f':
            print ("processesing", value, "...")
            feedMascot2BFabric(value)

if DBwritten:
    print ("dumping json file '{}' ...".format(DBfilename))
    json.dump(DB, open(DBfilename, 'w'), sort_keys=True, indent=4)

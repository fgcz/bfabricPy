#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""
# $HeadURL: https://fgcz-svn.uzh.ch/repos/fgcz/computer/fgcz-s-018/bfabric-feeder/fgcz_dataFeederMascot.py $
# $Id: fgcz_dataFeederMascot.py 9097 2021-02-05 15:38:38Z cpanse $
# $Date: 2021-02-05 16:38:38 +0100 (Fri, 05 Feb 2021) $


# Author
2012-10-08 Christian Panse <cp@fgcz.ethz.ch>
2012-10-10 Christian Panse <cp@fgcz.ethz.ch>
2012-10-11 Christian Panse <cp@fgcz.ethz.ch>
2021-01-06 Christian Panse <cp@fgcz.ethz.ch> - replace multiprocess by caching strategy
2023-10-20 Christian Panse <cp@fgcz.ethz.ch> - add timestamp

# Usage

find /usr/local/mascot/data/ -type f -mtime -1 -name "*dat" \
  | /home/cpanse/__checkouts/bfabricPy/bfabric/scripts/bfabric_feeder_mascot.py --stdin

# Crontab
0   0      *       *       7       nice -19 /usr/local/fgcz-s-018/bfabric-feeder/run_fgcz_dataFeederMascot.bash 365 2>&1 >/dev/null
3   */2       *       *       1-6       nice -19 /usr/local/fgcz-s-018/bfabric-feeder/run_fgcz_dataFeederMascot.bash 7 2>&1 >/dev/null
*/7   5-22       *       *       1-5     nice -19  /usr/local/fgcz-s-018/bfabric-feeder/run_fgcz_dataFeederMascot.bash 1  2>&1 >/dev/null
"""

import os
import re
import sys
import urllib
import hashlib
import getopt
from suds.client import Client
from datetime import datetime
import json
import itertools
import http.client
http.client.HTTPConnection._http_vsn = 10
http.client.HTTPConnection._http_vsn_str = 'HTTP/1.0'

workuniturl = 'http://fgcz-bfabric.uzh.ch/bfabric/workunit?wsdl'
clientWorkUnit = Client(workuniturl)
BFLOGIN = 'pfeeder'
BFPASSWORD = '!ForYourEyesOnly!'

DB = dict()
DBfilename = f"{os.getenv('HOME')}/mascot.json"
DBwritten = False

try:
    DB = json.load(open(DBfilename))
    print("Read {len} data items from {name} using {size:.1f} GBytes.".format(len=len(DB),
        name=DBfilename,
        size=sum(map(lambda x: int(x['resource']['size']), DB.values())) / (1024 * 1024 * 1024)))
except:
    print(f"loading '{DBfilename}' failed")
    pass


def signal_handler(signal, frame):
    print(("sys exit 1; signal=" + str(signal) + "; frame=" + str(frame)))
    sys.exit(1)


# TODO(cp): read .bfabricrc.py
def read_bfabricrc():
    with open(os.environ['HOME'] + "/.bfabricrc") as myfile:
        for line in myfile:
            return (line.strip())


def query_mascot_result(f):
    global DBwritten
    regex2 = re.compile(".*.+/(data/.+\.dat)$")
    regex2Result = regex2.match(f)
    if True:
        print(f"{datetime.now()} input>")
        print(f"\t{f}")
        if f in DB:
            print("\thit")
            wu = DB[f]
            if 'workunitid' in wu:
                print(f"\tdat file {f} already registered as workunit id {wu['workunitid']}. continue ...")
                return
            else:
                print('\tno workunitid found')
        else:
            print(f"\tparsing mascot result file '{f}'...")
            wu = parse_mascot_result_file(f)
            print(f"\tupdating cache '{DBfilename}' file ...")
            DBwritten = True
            DB[f] = wu

        if len(wu['inputresource']) > 0:
            if re.search("autoQC4L", wu['name']) or re.search("autoQC01", wu['name']):
                print(f"WARNING This script ignores autoQC based mascot dat file {f}.")
                return

            print("\tquerying bfabric ...")

            # jsut in case
            if 'errorreport' in wu:
                del (wu['errorreport'])

            try:
                resultClientWorkUnit = clientWorkUnit.service.checkandinsert(
                    dict(login=BFLOGIN, password=BFPASSWORD, workunit=wu))
            except ValueError:
                print(f"Exception {ValueError}")
                raise

            try:
                rv = resultClientWorkUnit.workunit[0]
            except ValueError:
                print(f"Exception {ValueError}")
                raise

            print(f"{datetime.now()} output>")
            if 'errorreport' in rv:
                print(f"\tfound errorreport '{rv['errorreport']}'.")

            if '_id' in rv:
                wu['workunitid'] = rv['_id']
                print(f"\tfound workunitid'{wu['workunitid']}'.")
                DB[f] = wu
                DBwritten = True

            if not '_id' in rv and not 'errorreport' in rv:
                print("something went wrong.")
                raise
                # print(resultClientWorkUnit)
                # print("exception for file {} with error {}".format(f, e))
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


def parse_mascot_result_file(f):

    # Getting the current date and time
    print(f"{datetime.now()} DEBUG parse_mascot_result_file")

    regex0 = re.compile("^title=.*(p([0-9]+).+Proteomics.*(raw|RAW|wiff)).*")
    regex3 = re.compile("^(FILE|COM|release|USERNAME|USERID|TOL|TOLU|ITOL|ITOLU|MODS|IT_MODS|CHARGE|INSTRUMENT|QUANTITATION|DECOY)=(.+)$")

    # control_chars = ''.join(map(chr, [range(0x00, 0x20) , range(0x7f, 0xa0)]))
    control_chars = ''.join(map(chr, itertools.chain(range(0x00, 0x20), range(0x7f, 0xa0))))

    control_char_re = re.compile(f'[{re.escape(control_chars)}]')

    line_count = 0
    meta_data_dict = dict(COM='', FILE='', release='', relativepath=f.replace('/usr/local/mascot/', ''))
    inputresourceHitHash = dict()
    inputresourceList = list()
    md5 = hashlib.md5()
    project = -1
    desc = ""
    with open(f) as dat:
        for line in dat:
            line_count = line_count + 1
            md5.update(line.encode())
            # check if the first character of the line is a 't' for title to save regex time
            if line[0] == 't':
                # result = regex0.match(urllib.url2pathname(line.strip()).replace('\\', "/").replace("//", "/"))
                result = regex0.match(urllib.parse.unquote(line.strip()).replace('\\', "/").replace("//", "/"))
                if result and not result.group(1) in inputresourceHitHash:
                    inputresourceHitHash[result.group(1)] = result.group(2)
                    inputresourceList.append(dict(storageid=2, relativepath=result.group(1)))
                    project = result.group(2)
                else:
                    # nothing as do be done since the input_resource is already recorded
                    pass
            elif line_count < 600:
                # none of the regex3 pattern is starting with 't'
                # result = regex3.match(urllib.url2pathname(line.strip()))
                result = regex3.match(urllib.parse.unquote(line.strip()))
                if result:
                    desc = desc + result.group(1) + "=" + result.group(2) + "; "
                    meta_data_dict[result.group(1)] = result.group(2)

    desc = desc.encode('ascii', errors='ignore')

    name = f"{meta_data_dict['COM']}; {os.path.basename(meta_data_dict['relativepath'])}"[:255]

    rv = dict(
        applicationid=19,
        containerid=project,
        name=control_char_re.sub('', name),
        description=control_char_re.sub('', desc.decode()),
        inputresource=inputresourceList,
        resource=dict(
            name=meta_data_dict['relativepath'],
            storageid=4,
            status='available',
            relativepath=meta_data_dict['relativepath'],
            size=os.path.getsize(f),
            filechecksum=md5.hexdigest()
        )
    )
    #TODO

    print(f"{datetime.now()}")
    print(rv)
    print("DEBUG END")

    return (rv)


def printFrequency(S):
    count = dict()
    for x in S:
        if x in count:
            count[x] = count[x] + 1
        else:
            count[x] = 1

    for key in sorted(count.keys(), key=lambda key: int(key)):
        print(f"p{key}\t{count[key]}")


def statistics():
    print("Statistics ...")
    print(f"len(DB)\t=\t{len(DB)}")
    printFrequency(map(lambda x: x['containerid'], DB.values()))
    print(f"file size\t=\t{sum(map(lambda x: int(x['resource']['size']), DB.values())) / (1024 * 1024 * 1024)} GBytes")

    # printFrequency(map(lambda x: x['description'].split(";"), DB.values()))
    # print(json.dumps(list(DB.values())[100], indent=4))


if __name__ == "__main__":
    BFPASSWORD = read_bfabricrc()
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:s", ["file=", "stdin", "statistics"])
    except getopt.GetoptError as err:
        print(str(err))
        sys.exit(2)

    for o, value in opts:
        if o == "--stdin":
            print("reading file names from stdin ...")
            for f in sys.stdin.readlines():
                query_mascot_result(f.strip())
        elif o == "--file" or o == '-f':
            print("processesing", value, "...")
            query_mascot_result(value)
        elif o == "--statistics" or o == '-s':
            statistics()
            sys.exit(0)

if DBwritten:
    print(f"dumping json file '{DBfilename}' ...")
    json.dump(DB, open(DBfilename, 'w'), sort_keys=True, indent=4)
    sys.exit(0)


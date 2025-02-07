#!/usr/bin/env python3
"""
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

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import re
import sys
import urllib
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from suds.client import Client

workuniturl = "http://fgcz-bfabric.uzh.ch/bfabric/workunit?wsdl"
clientWorkUnit = Client(workuniturl)
BFLOGIN = "pfeeder"
BFPASSWORD = "!ForYourEyesOnly!"

DB = {}
DBfilename = Path.home() / "mascot.json"

try:
    with DBfilename.open() as file:
        DB = json.load(file)
    print(
        "Read {len} data items from {name} using {size:.1f} GBytes.".format(
            len=len(DB),
            name=DBfilename,
            size=sum(map(lambda x: int(x["resource"]["size"]), DB.values())) / (1024 * 1024 * 1024),
        )
    )
except OSError:
    print(f"loading '{DBfilename}' failed")
    pass


def query_mascot_result(file_path: str) -> bool:
    db_written = False
    print(f"{datetime.now()} input>")
    print(f"\t{file_path}")
    if file_path in DB:
        print("\thit")
        wu = DB[file_path]
        if "workunitid" in wu:
            print(f"\tdat file {file_path} already registered as workunit id {wu['workunitid']}. continue ...")
            return
        else:
            print("\tno workunitid found")
    else:
        print(f"\tparsing mascot result file '{file_path}'...")
        wu = parse_mascot_result_file(file_path)
        print(f"\tupdating cache '{DBfilename}' file ...")
        db_written = True
        DB[file_path] = wu

    if len(wu["inputresource"]) > 0:
        if re.search("autoQC4L", wu["name"]) or re.search("autoQC01", wu["name"]):
            print(f"WARNING This script ignores autoQC based mascot dat file {file_path}.")
            return

        print("\tquerying bfabric ...")

        # just in case
        if "errorreport" in wu:
            del wu["errorreport"]

        try:
            resultClientWorkUnit = clientWorkUnit.service.checkandinsert(
                dict(login=BFLOGIN, password=BFPASSWORD, workunit=wu)
            )
        except ValueError:
            print(f"Exception {ValueError}")
            raise

        try:
            rv = resultClientWorkUnit.workunit[0]
        except ValueError:
            print(f"Exception {ValueError}")
            raise

        print(f"{datetime.now()} output>")
        if "errorreport" in rv:
            print(f"\tfound errorreport '{rv['errorreport']}'.")

        if "_id" in rv:
            wu["workunitid"] = rv["_id"]
            print(f"\tfound workunitid'{wu['workunitid']}'.")
            DB[file_path] = wu
            db_written = True

        if "_id" not in rv and "errorreport" not in rv:
            print("something went wrong.")
            raise
            # print(resultClientWorkUnit)
            # print("exception for file {} with error {}".format(f, e))

    return db_written


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


def parse_mascot_result_file(file_path: str) -> dict[str, Any]:
    # Getting the current date and time
    print(f"{datetime.now()} DEBUG parse_mascot_result_file")

    regex0 = re.compile("^title=.*(p([0-9]+).+Proteomics.*(raw|RAW|wiff)).*")
    regex3 = re.compile(
        "^(FILE|COM|release|USERNAME|USERID|TOL|TOLU|ITOL|ITOLU|MODS|IT_MODS|CHARGE|INSTRUMENT|QUANTITATION|DECOY)=(.+)$"
    )

    control_chars = "".join(map(chr, itertools.chain(range(0x00, 0x20), range(0x7F, 0xA0))))
    control_char_re = re.compile(f"[{re.escape(control_chars)}]")

    line_count = 0
    meta_data_dict = dict(
        COM="",
        FILE="",
        release="",
        relativepath=file_path.replace("/usr/local/mascot/", ""),
    )
    inputresourceHitHash = dict()
    inputresourceList = list()
    md5 = hashlib.md5()
    project = -1
    desc = ""
    with Path(file_path).open() as dat:
        for line in dat:
            line_count = line_count + 1
            md5.update(line.encode())
            # check if the first character of the line is a 't' for title to save regex time
            if line[0] == "t":
                result = regex0.match(urllib.parse.unquote(line.strip()).replace("\\", "/").replace("//", "/"))
                if result and result.group(1) not in inputresourceHitHash:
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

    desc = desc.encode("ascii", errors="ignore")
    name = f"{meta_data_dict['COM']}; {os.path.basename(meta_data_dict['relativepath'])}"[:255]
    rv = dict(
        applicationid=19,
        containerid=project,
        name=control_char_re.sub("", name),
        description=control_char_re.sub("", desc.decode()),
        inputresource=inputresourceList,
        resource=dict(
            name=meta_data_dict["relativepath"],
            storageid=4,
            status="available",
            relativepath=meta_data_dict["relativepath"],
            size=os.path.getsize(file_path),
            filechecksum=md5.hexdigest(),
        ),
    )
    # TODO

    print(f"{datetime.now()}")
    print(rv)
    print("DEBUG END")

    return rv


def print_project_frequency(project_numbers: list[int | str]) -> None:
    """Prints the frequency of the project numbers in the list, assuming they are either integers or strings of
    individual integers."""
    count = Counter(project_numbers)
    for key in sorted(count.keys(), key=int):
        print(f"p{key}\t{count[key]}")


def print_statistics() -> None:
    """Prints statistics about the provided database."""
    print("Statistics ...")
    print(f"len(DB)\t=\t{len(DB)}")
    print_project_frequency(map(lambda x: x["containerid"], DB.values()))
    print(
        "file size\t=\t{} GBytes".format(
            sum(map(lambda x: int(x["resource"]["size"]), DB.values())) / (1024 * 1024 * 1024)
        )
    )


def main() -> None:
    """Parses the CLI arguments and calls the appropriate functions."""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stdin", action="store_true", help="read file names from stdin")
    group.add_argument("--file", type=str, help="processes the provided file")
    parser.add_argument("--statistics", action="store_true", help="print statistics")

    args = parser.parse_args()

    db_written = False
    if args.stdin:
        print("reading file names from stdin ...")
        for filename in sys.stdin.readlines():
            db_written = query_mascot_result(filename.strip()) or db_written
    elif args.file:
        print("processesing", args.file, "...")
        db_written = query_mascot_result(args.file)
    if args.statistics:
        print_statistics()

    if db_written:
        print(f"dumping json file '{DBfilename}' ...")
        with DBfilename.open("w") as file:
            json.dump(DB, file, sort_keys=True, indent=4)


if __name__ == "__main__":
    main()

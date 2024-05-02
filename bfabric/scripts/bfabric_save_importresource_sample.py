#!/usr/bin/python3
# -*- coding: latin1 -*-

"""General Importresource Feeder for bfabric

Author:
    Christian Panse <cp@fgcz.ethz.ch>, 2012-2024

Usage:
    runs under www-data credentials

    $ echo "906acd3541f056e0f6d6073a4e528570;1345834449;46342144;p996/Proteomics/TRIPLETOF_1/jonas_20120820_SILAC_comparison/ 20120824_01_NiKu_1to5_IDA_rep2.wiff" | bfabric_save_importresource_sample.py - 

History:
    The first version of the script appeared on Wed Oct 24 17:02:04 CEST 2012. 
"""


import logging
import logging.handlers
import os
import re
import sys
import time

from bfabric.bfabric2 import Bfabric
from bfabric.bfabric2 import get_system_auth

BFABRIC_STORAGE_ID = 2


def save_importresource(client: Bfabric, line: str):
    """reads, splits and submit the input line to the bfabric system
    Input: a line containg
    md5sum;date;size;path

    "906acd3541f056e0f6d6073a4e528570;
    1345834449;
    46342144;
    p996/Proteomics/TRIPLETOF_1/jonas_20120820/20120824_01_NiKu_1to5_IDA_rep2.wiff"

    Output:
        True on success otherwise an exception raise
    """
    mdf5_checksum, file_date, file_size, file_path = line.split(";")

    # Format the timestamp for bfabric
    file_date = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(int(file_date)))

    bfabric_application_ids = client.config.application_ids
    if not bfabric_application_ids:
        raise RuntimeError("No bfabric_application_ids configured. check '~/.bfabricpy.yml' file!")

    bfabric_application_id, bfabric_projectid = get_bfabric_application_and_project_id(
        bfabric_application_ids, file_path
    )

    obj = {
        "applicationid": bfabric_application_id,
        "filechecksum": mdf5_checksum,
        "containerid": bfabric_projectid,
        "filedate": file_date,
        "relativepath": file_path,
        "name": os.path.basename(file_path),
        "size": file_size,
        "storageid": BFABRIC_STORAGE_ID,
    }

    try:
        m = re.search(
            r"p([0-9]+)\/(Proteomics\/[A-Z]+_[1-9])\/.*_\d\d\d_S([0-9][0-9][0-9][0-9][0-9][0-9]+)_.*(raw|zip)$",
            file_path,
        )
        print("found sampleid={} pattern".format(m.group(3)))
        obj["sampleid"] = int(m.group(3))
    except Exception:
        pass

    print(obj)
    res = client.save(endpoint="importresource", obj=obj).to_list_dict()
    print(res[0])


def get_bfabric_application_and_project_id(bfabric_application_ids, file_path):
    # linear search through dictionary. first hit counts!
    bfabric_applicationid = -1
    bfabric_projectid = (-1,)
    for i in bfabric_application_ids.keys():
        # first match counts!
        if re.search(i, file_path):
            bfabric_applicationid = bfabric_application_ids[i]
            re_result = re.search(r"^p([0-9]+)\/.+", file_path)
            bfabric_projectid = re_result.group(1)
            break
    if bfabric_applicationid < 0:
        logger = logging.getLogger("sync_feeder")
        logger.error("{0}; no bfabric application id.".format(file_path))
        raise RuntimeError("no bfabric application id.")
    return bfabric_applicationid, bfabric_projectid


def setup_logger():
    logger = logging.getLogger("sync_feeder")
    hdlr_syslog = logging.handlers.SysLogHandler(address=("130.60.81.21", 514))
    formatter = logging.Formatter("%(name)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    hdlr_syslog.setFormatter(formatter)
    logger.addHandler(hdlr_syslog)
    logger.setLevel(logging.INFO)


def main():
    setup_logger()
    client = Bfabric(*get_system_auth())
    if sys.argv[1] == "-":
        print("reading from stdin ...")
        for input_line in sys.stdin:
            save_importresource(client, input_line.rstrip())
    elif sys.argv[1] == "-h":
        print(__doc__)
    else:
        save_importresource(client, sys.argv[1])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

"""
feeds autoQC runs into bfabric
by Christian Panse <cp@fgcz.ethz.ch> November 2018

an bash code snippet how it can be used:

tail -n 1000 /srv/www/htdocs/Data2San/sync_LOGS/pfiles.txt \
  | egrep "_autoQC01.*raw$" \
  | tail -n 1 \
  | ./bfabric/scripts/bfabric_feeder_resource_autoQC.py
"""

import os
import re
import sys
import time
import unittest

from bfabric import Bfabric


class AutoQC:
    """
    feeder for autoQC raw files
    """

    def __init__(self) -> None:
        self.bfabric_storageid = 2
        self.client = Bfabric.connect()
        self.bfabric_application_ids = self.client.config.application_ids

    @property
    def get_id(self, obj) -> int:
        print("==============")
        print(obj)
        print(f"DEBGUG obj: {obj[0]._id}")
        return int(obj[0]._id)

    def sample_check(self, projectid: int, name: str):
        """
        checks wether a S exists or not. if not the S is created.
        :param projectid:
        :param name:
        :return: SID
        """
        try:
            res = self.client.read(endpoint="sample", obj={"containerid": projectid, "name": name}).to_list_dict()
        except Exception:
            print(res)
            raise

        sample_type = "Biological Sample - Proteomics"

        query_autoQC01 = {
            "name": f"{name}",
            "type": sample_type,
            "containerid": projectid,
            "species": "Bos taurus",
            "groupingvar": "A",
            "samplingdate": "2018-11-15",
            "description": "core4life standard: sample BSA + iRT 1:800",
        }

        query_autoQC4L = {
            "name": f"{name}",
            "type": sample_type,
            "containerid": projectid,
            "species": "n/a",
            "groupingvar": "A",
            "samplingdate": "2018-11-15",
            "description": "core4life standard: 6 x 5 LC-MS/MS Peptide Reference Mix",
        }

        query_lipidQC01 = {
            "name": f"{name}",
            "type": "Biological Sample - Metabolomics",
            "containerid": projectid,
            "species": "n/a",
            "extractionprotocolannotation": "n/a",
            "organismpart": "n/a",
            "compoundclass": "Lipids",
            "description": "Lipidmix containing 2uM of FFA, BA, LPC. positive mode, C18.",
        }

        if not res:
            if name == "autoQC4L":
                res = self.client.save(endpoint="sample", obj=query_autoQC4L).to_list_dict()
            elif name == "autoQC01":
                res = self.client.save(endpoint="sample", obj=query_autoQC01).to_list_dict()
            elif name == "lipidQC01":
                res = self.client.save(endpoint="sample", obj=query_lipidQC01).to_list_dict()

        print(res)
        print(res[0])
        return res[0]["id"]

    def workunit_check(self, projectid: int, name: str, applicationid: int):
        """

        checks wether a WU exists or not. if not the WU is created.

        :param projectid:
        :param name:
        :param applicationid:
        :return: int WUID
        """

        query = {"projectid": projectid, "name": name, "applicationid": applicationid}
        res = self.client.read(endpoint="workunit", obj=query).to_list_dict()

        description = """
contains automatic registered quality control (QC)
measurements of the corresponding mass spec device.
For the QC analysis please check the following tools
listed below.
"""

        if name == "autoQC4L":
            links = [
                "http://fgcz-ms.uzh.ch/~cpanse/autoQC4L.html",
                "http://fgcz-ms-shiny.uzh.ch:8080/bfabric_rawDiag/",
                "http://qcloud.crg.eu",
                "https://panoramaweb.org",
            ]
        elif name == "autoQC01":
            links = [
                "http://fgcz-ms.uzh.ch/~cpanse/autoQC01.html",
                "http://fgcz-ms-shiny.uzh.ch:8080/bfabric_rawDiag/",
                "http://qcloud.crg.eu",
                "https://panoramaweb.org",
            ]
        elif name == "lipidQC01":
            description = "Contains automatic registered quality control (QC) measurements, positive mode."
            links = ["http://fgcz-ms.uzh.ch/~cpanse/lipidQC01.html"]

        if not res:
            query = {
                "projectid": projectid,
                "name": name,
                "applicationid": applicationid,
                "description": description,
                "link": links,
            }

            res = self.client.save(endpoint="workunit", obj=query).to_list_dict()

        return res[0]["id"]

    def resource_check(
        self,
        projectid: int,
        name: str,
        workunitid: int,
        filename: str,
        filedate,
        size,
        md5,
        sampleid,
    ):
        """
        checks wether a R exists or not. if not the R is created.
        :param projectid:
        :param name:
        :param workunitid:
        :param filename:
        :param filedate:
        :param size:
        :param md5:
        :param sampleid:
        :return: RID
        """

        # the time format bfabric understands
        _file_date = time.strftime("%FT%H:%M:%S-01:00", time.gmtime(int(filedate)))

        query = {
            "filechecksum": md5,
            "workunitid": workunitid,
            "projectid": projectid,
        }
        res = self.client.read(endpoint="resource", obj=query).to_list_dict()

        if not res:
            query = {
                "workunitid": workunitid,
                "sampleid": sampleid,
                "filechecksum": md5,
                "relativepath": filename,
                "name": os.path.basename(filename),
                "status": "available",
                "size": size,
                "storageid": self.bfabric_storageid,
            }

            res = self.client.save(endpoint="resource", obj=query).to_list_dict()

            query = {"id": workunitid, "status": "available"}
            self.client.save(endpoint="workunit", obj=query).to_list_dict()

        return res[0]["id"]

    def feed(self, line) -> None:
        """
        feeds one line example:
        :param line:
        :return:
        """

        try:
            (_md5, _file_date, _file_size, filename) = line.split(";")
        except Exception:
            return

        try:
            m = re.search(
                r"p([0-9]+)\/((Metabolomics|Proteomics)\/[A-Z]+_[1-9])\/.*(autoQC01|autoQC4L|lipidQC01).+raw$",
                filename,
            )

            projectid = m.group(1)
            applicationid = self.bfabric_application_ids[m.group(2)]
            autoQCType = m.group(4)

        except Exception:
            print(f"# no match '{filename}'.")
            return

        print(f"{projectid}\t{applicationid}\t{autoQCType}\n")

        try:
            sampleid = self.sample_check(projectid, name=autoQCType)
            sys.exit(0)
            # print sampleid
            workunitid = self.workunit_check(projectid, name=autoQCType, applicationid=applicationid)
            # print "WUID={}".format(workunitid)

            resourceid = self.resource_check(
                projectid=projectid,
                name=os.path.basename(filename),
                workunitid=workunitid,
                filename=filename,
                filedate=_file_date,
                size=_file_size,
                md5=_md5,
                sampleid=sampleid,
            )

            # sampleid=0
            print(f"p{projectid}\tA{applicationid}\t{filename}\tS{sampleid}\tWU{workunitid}\tR{resourceid}")
        except Exception as err:
            print(f"# Failed to register to bfabric: {err}")


class TestCaseAutoQC(unittest.TestCase):
    """
    python -m unittest bfabric_feeder_resource_autoQC

    """

    BF = AutoQC()

    def setUp(self) -> None:
        pass

    def test_feed(self) -> None:
        line = "61cf7e172713344bdf6ebe5b1ed61d99;1549963879;306145606;p2928/Proteomics/QEXACTIVEHF_2/ciuffar_20190211_190211_TNF_PRM_rT_again_AQUA_LHration/20190211_013_autoQC4L.raw"
        # self.BF.feed(line)
        line = "efdf5e375d6e0e4e4abf9c2b3e1e97d5;1542134408;59129652;p1000/Proteomics/QEXACTIVEHF_2/tobiasko_20181113/20181113_003_autoQC01.raw"
        # self.BF.feed(line)
        line = "d0412c1aae029d21bb261c1e4c682ea9;1549441215;207803452;p2947/Metabolomics/QEXACTIVE_3/sstreb_20190206_o5292/p2947_o5292_20190205_FFA_BA_LPC_2um_lipidQC01_1.raw"
        self.BF.feed(line)


if __name__ == "__main__":
    BF = AutoQC()
    for input_line in sys.stdin:
        BF.feed(input_line.rstrip())

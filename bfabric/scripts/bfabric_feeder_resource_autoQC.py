#!/usr/bin/python

"""
feeds autoQC runs into bfabric
by Christian Panse <cp@fgcz.ethz.ch> November 2018

an bash code snippet how it can be used:

tail -n 1000 ~/Downloads/pfiles.txt \
  | grep p1000 \
  | grep raw$ \
  | grep autoQC01 \
  | head \
  | ./bfabric_autoQC.py
"""

import sys
import os
import re
import time
import unittest
from bfabric import Bfabric


class autoQC():
    """
        feeder for autoQC raw files
    """
    bfabric_storageid = 2
    bfabric_application_ids = {'Proteomics/TOFTOF_2': 91,
                               'Proteomics/T100_1': 18,
                               'Proteomics/TRIPLETOF_1': 93,
                               'Proteomics/VELOS_1': 90,
                               'Proteomics/VELOS_2': 89,
                               'Proteomics/ORBI_1': 10,
                               'Proteomics/ORBI_2': 12,
                               'Proteomics/ORBI_3': 87,
                               'Proteomics/G2HD_1': 128,
                               'Proteomics/LTQ_1': 7,
                               'Proteomics/LTQFT_1': 8,
                               'Proteomics/QTRAP_1': 92,
                               'Proteomics/TSQ_1': 15,
                               'Proteomics/TSQ_2': 53,
                               'Proteomics/Analysis/Progenesis': 84,
                               'Proteomics/Analysis/ProteinPilot': 148,
                               'Proteomics/Analysis/MaxQuant': 151,
                               'Proteomics/Analysis/GenericZip': 185,
                               'Proteomics/QEXACTIVE_1': 160,
                               'Proteomics/QEXACTIVE_2': 161,
                               'Proteomics/QEXACTIVE_3': 163,
                               'Proteomics/FUSION_1': 162,
                               'Proteomics/FUSION_2': 176,
                               'Proteomics/LUMOS_1': 248,
                               'Proteomics/QEXACTIVEHF_1': 177,
                               'Proteomics/QEXACTIVEHF_2': 197,
                               'Proteomics/QEXACTIVEHF_3': 207,
                               'Proteomics/PROTEONXPR36': 82,
                               'Proteomics/EXTERNAL_0': 188,
                               'Proteomics/EXTERNAL_1': 189,
                               'Proteomics/EXTERNAL_2': 190,
                               'Proteomics/EXTERNAL_3': 191,
                               'Proteomics/EXTERNAL_4': 192,
                               'Proteomics/EXTERNAL_5': 193,
                               'Proteomics/QEXACTIVEHFX_1': 232,
                               'Metabolomics/QEXACTIVE_3': 171,
                               'Metabolomics/TRIPLETOF_1': 144,
                               'Metabolomics/TOFTOF_2': 143,
                               'Metabolomics/QTOF': 14,
                               'Metabolomics/LTQFT_1': 9,
                               'Metabolomics/G2HD_1': 81,
                               'Metabolomics/TSQ_1': 16,
                               'Metabolomics/TSQ_2': 43,
                               'Metabolomics/GCT_1': 44,
                               'Metabolomics/ORBI_1': 11,
                               'Metabolomics/ORBI_2': 13,
                               'Metabolomics/IMSTOF_1': 203,
                               'Metabolomics/QUANTIVA_1': 214,
                               'Metabolomics/Analysis/ProgenesisQI': 226,
                               'Metabolomics/ORBI_3': 77}

    bfapp = Bfabric(verbose=False)

    @property
    def getId(self, obj):
        print("==============")
        print(obj)

        try:
            print("DEBGUG obj: {}".format(obj[0]._id))
            return int(obj[0]._id)
        except:
            raise

    def __init__(self):
        pass

    def sample_check(self, projectid, name):
        """
        checks wether a S exists or not. if not the S is created.
        :param projectid:
        :param name:
        :return: SID
        """

        try:
            res = self.bfapp.read_object(endpoint='sample',
                                         obj={'projectid': projectid, 'name': name})
        except:
            raise

        sample_type = 'Biological Sample - Proteomics'
        
        query_autoQC01 = {'name': "{}".format(name),
                          'type': sample_type,
                          'projectid': projectid,
                          'species': "Bos taurus",
                          'groupingvar': "A",
                          'samplingdate': "2018-11-15",
                          'description': 'core4life standard: sample BSA + iRT 1:800'}

        query_autoQC4L = {'name': "{}".format(name),
                          'type': sample_type,
                          'projectid': projectid,
                          'species': "n/a",
                          'groupingvar': "A",
                          'samplingdate': "2018-11-15",
                          'description': 'core4life standard: 6 x 5 LC-MS/MS Peptide Reference Mix'}

        query_lipidQC01 = {'name': "{}".format(name),
                          'type': 'Biological Sample - Metabolomics',
                          'projectid': projectid,
                          'species': "n/a",
                          'extractionprotocolannotation': "n/a",
                          'organismpart': "n/a",
                          'compoundclass': "Lipids",
                          'description': 'Lipidmix containing 2uM of FFA, BA, LPC. positive mode, C18.'}

        if res is None:
            if name == 'autoQC4L':
                res = self.bfapp.save_object(endpoint='sample', obj=query_autoQC4L)
            elif name == 'autoQC01':
                res = self.bfapp.save_object(endpoint='sample', obj=query_autoQC01)
            elif name == 'lipidQC01':
                res = self.bfapp.save_object(endpoint='sample', obj=query_lipidQC01)

        return res[0]._id

    def workunit_check(self, projectid, name, applicationid):
        """

        checks wether a WU exists or not. if not the WU is created.

        :param projectid:
        :param name:
        :param applicationid:
        :return: int WUID
        """

        query = {'projectid': projectid, 'name': name, 'applicationid': applicationid}
        try:
            res = self.bfapp.read_object(endpoint='workunit', obj=query)
        except:
            raise

        description = """
contains automatic registered quality control (QC)
measurements of the corresponding mass spec device.
For the QC analysis please check the following tools
listed below.
"""

        if name == 'autoQC4L':
            links = ['http://fgcz-ms.uzh.ch/~cpanse/autoQC4L.html',
                     'http://fgcz-ms-shiny.uzh.ch:8080/bfabric_rawDiag/',
                     'http://qcloud.crg.eu',
                     'https://panoramaweb.org']
        elif name == 'autoQC01':
            links = ['http://fgcz-ms.uzh.ch/~cpanse/autoQC01.html',
                     'http://fgcz-ms-shiny.uzh.ch:8080/bfabric_rawDiag/',
                     'http://qcloud.crg.eu',
                     'https://panoramaweb.org']
        elif name == 'lipidQC01':
            description = "Contains automatic registered quality control (QC) measurements, positive mode."
            links = ['http://fgcz-ms.uzh.ch/~cpanse/lipidQC01.html'] 

        if res is None:
            query = {'projectid': projectid, 'name': name,
                     'applicationid': applicationid,
                     'description': description,
                     'link': links}

            res = self.bfapp.save_object(endpoint='workunit',
                                         obj=query)

        else:
            pass

        return res[0]._id

    def resource_check(self, projectid, name, workunitid, filename, filedate, size, md5, sampleid):
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
            'filechecksum': md5,
            'workunitid': workunitid,
            'projectid': projectid,
        }
        try:
            res = self.bfapp.read_object(endpoint='resource', obj=query)
        except:
            raise

        if res is None:
            query = {
                'workunitid': workunitid,
                'sampleid': sampleid,
                'filechecksum': md5,
                'relativepath': filename,
                'name': os.path.basename(filename),
                'status': 'available',
                'size': size,
                'storageid': self.bfabric_storageid
            }

            res = self.bfapp.save_object(endpoint='resource', obj=query)

            query = {'id': workunitid, 'status': 'available'}
            res2 = self.bfapp.save_object(endpoint='workunit', obj=query)

        return res[0]._id



    def feed(self, line):
        """
        feeds one line example:
        :param line:
        :return:
        """


        try:
            (_md5, _file_date, _file_size, filename) = line.split(";")
        except Exception as err:
            return

        try:
            m = re.search(r"p([0-9]+)\/((Metabolomics|Proteomics)\/[A-Z]+_[1-9])\/.*(autoQC01|autoQC4L|lipidQC01).+raw$",
                          filename)

            projectid = m.group(1)
            applicationid = self.bfabric_application_ids[m.group(2)]
            autoQCType = m.group(4)

        except Exception as err:
            print(("# no match '{}'.".format(filename)))
            return

        try:
            sampleid = self.sample_check(projectid, name=autoQCType)
            #print sampleid
            workunitid = self.workunit_check(projectid, name=autoQCType, applicationid=applicationid)
            #print "WUID={}".format(workunitid)

            resourceid = self.resource_check(projectid=projectid, name=os.path.basename(filename),
                                              workunitid=workunitid,
                                              filename=filename,
                                              filedate=_file_date,
                                              size=_file_size,
                                              md5=_md5,
                                              sampleid=sampleid)

            # sampleid=0
            print(("p{p}\tA{A}\t{filename}\tS{S}\tWU{WU}\tR{R}".format(p=projectid,
                                                                       A=applicationid,
                                                                       filename=filename,
                                                                       S=sampleid,
                                                                       WU=workunitid,
                                                                       R=resourceid)))
        except Exception as err:
            print(('# Failed to register to bfabric: {}'.format(err)))


class TestCaseAutoQC(unittest.TestCase):
    """
    python -m unittest bfabric_feeder_resource_autoQC

    """
    BF = autoQC()

    def setUp(self):
        pass

    def test_feed(self):
        line = "61cf7e172713344bdf6ebe5b1ed61d99;1549963879;306145606;p2928/Proteomics/QEXACTIVEHF_2/ciuffar_20190211_190211_TNF_PRM_rT_again_AQUA_LHration/20190211_013_autoQC4L.raw"
        #self.BF.feed(line)
        line = "efdf5e375d6e0e4e4abf9c2b3e1e97d5;1542134408;59129652;p1000/Proteomics/QEXACTIVEHF_2/tobiasko_20181113/20181113_003_autoQC01.raw"
        #self.BF.feed(line)
        line = "d0412c1aae029d21bb261c1e4c682ea9;1549441215;207803452;p2947/Metabolomics/QEXACTIVE_3/sstreb_20190206_o5292/p2947_o5292_20190205_FFA_BA_LPC_2um_lipidQC01_1.raw"
        self.BF.feed(line)

if __name__ == '__main__':

    BF = autoQC()
    for input_line in sys.stdin:
        BF.feed(input_line.rstrip())

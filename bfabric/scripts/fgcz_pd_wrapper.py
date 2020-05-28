#!/usr/bin/python
# -*- coding: latin1 -*-

# Copyright (C) 2017 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/fgcz_pd_wrapper.py $
# $Id: fgcz_pd_wrapper.py 2992 2017-08-17 13:37:36Z cpanse $

import logging
import logging.handlers
import os
import pprint
import re
import shutil
import subprocess
import sys
import time
import urllib.request, urllib.error, urllib.parse
from os import listdir
from optparse import OptionParser

import yaml
from lxml import etree

from bfabric import Bfabric

import hashlib


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def create_logger(name="MaxQuant"):
    """
    create a logger object
    """
    syslog_handler = logging.handlers.SysLogHandler(address=("130.60.81.148", 514))
    formatter = logging.Formatter('%(name)s %(message)s')
    syslog_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(20)
    logger.addHandler(syslog_handler)

    return logger


logger = create_logger()


class FgczPDWrapper:
    """

  input:
    QEXACTIVE_2:
    - bfabric@fgczdata.fgcz-net.unizh.ch://srv/www/htdocs//p1946/Proteomics/QEXACTIVE_2/paolo_20150811_course/20150811_01_Fetuin40fmol.raw
    - bfabric@fgczdata.fgcz-net.unizh.ch://srv/www/htdocs//p1946/Proteomics/QEXACTIVE_2/paolo_20150811_course/20150811_02_YPG1.raw
  output:
  - bfabric@fgczdata.fgcz-net.unizh.ch:/srv/www/htdocs//p1946/bfabric/Proteomics/MaxQuant_Scaffold_LFQ_tryptic_swissprot/2015/2015-09/2015-09-07//workunit_135076//203583.zip
  parameters: {}
  protocol: scp
    """

    config = None
    outputurl = None
    scratchroot = os.path.normcase(r"d:\scratch_")
    scratch = scratchroot

    def __init__(self, config=None):

        self.bf = Bfabric()
        if not os.path.isdir(self.scratchroot):
            try:
                os.mkdir(self.scratchroot)
            except:
                print("scratch '{0}' does not exists.".format(self.scratchroot))
                raise
        if config:
            self.config = config

    def run_commandline(self, cmd, shell_flag=False):
        """

        :param cmd:
        :param shell_flag:
        :return:
        """
        (pid, return_code) = (None, None)

        (out, err) = ("", "")
        tStart = time.time()

        logger.info(cmd)
        try:
            p = subprocess.Popen(cmd, shell=shell_flag)

            pid = p.pid
            return_code = p.wait()

            (out, err) = p.communicate()
            p.terminate()

        except OSError as e:
            msg = "exception|pid={0}|OSError={1}".format(pid, e)
            logger.info(msg)
            print(err)
            print(out)
            raise

        msg_info = "completed|pid={0}|time={1}|return_code={2}|cmd='{3}'" \
            .format(pid, time.time() - tStart, return_code, cmd)
        logger.info(msg_info)

        print(out)
        print(err)
        return (return_code)

    def map_url_scp2smb(self, url,
                        from_prefix_regex="bfabric@fgczdata.fgcz-net.unizh.ch://srv/www/htdocs",
                        to_prefix="\\\\130.60.81.21\\data"):
        """maps an url from

        'bfabric@fgczdata.fgcz-net.unizh.ch://srv/www/htdocs//p1946/Proteomics/QEXACTIVE_2/paolo_20150811_course/20150811_01_Fetuin40fmol.raw'

        to

        '\\130.60.81.21\data\p1946\proteomics\qexactive_2\paolo_20150811_course\20150811_01_fetuin40fmol.raw'

        if it can not be matched it returns None
        """

        regex = re.compile("({0}.+)(p[0-9]+([\\/]).*)$".format(from_prefix_regex))

        match = regex.match(url)

        if match:
            result_url = "{0}\{1}".format(to_prefix, os.path.normcase(match.group(2)))
            return (result_url)
        else:
            return None

    def print_config(self):
        print("------")
        pp = pprint.PrettyPrinter(width=70)
        pp.pprint(self.config)

        return True

    def add_config(self, config):
        self.config = config
        return True

    def add_outputurl(self, url=None):
        """

        :param url:
        :return:
        """
        self.outputurl = url
        return True

    def create_scratch(self):
        """create scratch space
        """

        # TODO(cp): what if workunit is not defined
        self.scratch = os.path.normcase(
            "{0}/W{1}".format(self.scratchroot, self.config['job_configuration']['workunit_id']))

        if not os.path.isdir(self.scratch):
            try:
                os.mkdir(self.scratch)
            except:
                logger.info("scratch '{0}' does not exists.".format(self.scratch))
                raise

        return True

    def scp(self, src, dst,
            scp_cmd=r"d:\fgcz\pscp.exe",
            scp_option=r"-scp -i D:\fgcz\id_rsa.ppk"
            ):
        """
         this is the scp wrapper for data staging

        :param src:
        :param dst:
        :param scp_cmd:
        :param scp_option:
        :return:
        """


        cmd = "{0} {1} {2} {3}".format(scp_cmd, scp_option, src, dst)
        self.run_commandline(cmd, shell_flag=False)
        return (True)

    def copy_input_to_scratch(self,
                              copy_method=lambda s, t: shutil.copyfile(s, t),
                              src_url_mapping=lambda x: x,
                              dst_url_mapping=lambda x: os.path.basename(x)):
        """
         make input resources available on scratch

         NOTE: we assume if the file is already in place it is identical to the src file.


        :param copy_method:
        :param src_url_mapping:
        :param dst_url_mapping:
        :return:
        """

        _input = self.config['application']['input']

        try:
            self._fsrc_fdst = []
            for i in list(_input.keys()):
                self._fsrc_fdst = self._fsrc_fdst + [(src_url_mapping(x), dst_url_mapping(x)) for x in _input[i]]

            for (_fsrc, _fdst) in self._fsrc_fdst:
                if os.path.isfile(_fdst):
                    logger.info("'{0}' is already there.".format(_fdst))
                    pass
                else:
                    try:
                        logger.info("copy '{0}' from '{1}' ...".format(_fdst, _fsrc))
                        copy_method(_fsrc, _fdst)
                    except:
                        print("ERROR: fail copy failed.")
                        raise

        except:
            logger.info("copying failed")
            raise

        return True

    """
        the following function have to be adapted
    """

    def stage_input(self):
        """

        :return:
        """

        logger.info("stage input data")
        self.copy_input_to_scratch(copy_method=lambda x, y: self.scp(x, y),
                                   dst_url_mapping=lambda x: os.path.normpath(r"{0}\{1}".format(self.scratch,
                                                                                                os.path.basename(x))))

    def create_pd_workflow_config(self, targetDir):
        try:
            url_processing = "{}/{}.pdProcessingWF".format(self.config['application']['parameters']['workflowbaseurl'],
                                                           self.config['application']['parameters']['workflow'])
            url_consensus = "{}/{}.pdConsensusWF".format(self.config['application']['parameters']['workflowbaseurl'],
                                                         self.config['application']['parameters']['workflow'])

        except:
            print('no url available')
            raise

        try:
            print(url_processing)
            config_processing = urllib.request.urlopen(url_processing).read()

            print(url_consensus)
            config_consesus = urllib.request.urlopen(url_consensus).read()
        except:
            print('url open failed.')
            raise

        try:
            tree = etree.parse(url_processing)
        except:
            print("parsing failed")
            raise

        for query, value in self.config['application']['parameters'].items():
            element = tree.find(query)
            if element is not None:
                if value == "None":
                    element.text = ''
                else:
                    element.text = value

        with open("{}\\bfabric.pdProcessingWF".format(targetDir), "w") as f:
            f.write(etree.tostring(tree))

        with open("{}\\bfabric.pdConsensusWF".format(targetDir), "w") as f:
            f.write(config_consesus)

        return True

    def get_filenames(self):
        try:
            _input = self.config['application']['input']
            filenames = [os.path.splitext(i)[0] for i in sum([list(map(os.path.basename, _input[i])) for i in list(_input.keys())], [])]

        except:
            print("can not extract filenames.")
            raise

        return filenames

    def get_resourceids(self):
        try:
            _input = self.config['job_configuration']['input']
            resourceids = [i['resource_id'] for i in sum([_input[k] for k in list(_input.keys())], [])]
        except:
            print("can not extract resourceid.")
            raise
        return resourceids

    def run_pd(self,
               PDcmd=r'"c:\Program Files\Thermo\Proteome Discoverer Daemon 2.1\System\Release\DiscovererDaemon.exe"',
               PDconfig=r"d:\pd\tk\tobi.pdProcessingWF;d:\pd\tk\tobi.pdConsensusWF"):

        logger.info("configure PD")

        with open("{}\\runme.bat".format(self.scratch), "w") as f:

            workunitid = self.config['job_configuration']['workunit_id']

            cmd_c = "{PD} -c W{workunitid}".format(PD=PDcmd, workunitid=workunitid)

            f.write("{}\n".format(cmd_c))





            for (filename, resouceid) in zip(self.get_filenames(), self.get_resourceids()):

                f.write("{PD} -a W{workunitid} {scratch}\\{filename}.raw\n".format(PD=PDcmd,
                                                                           workunitid=workunitid,
                                                                           scratch=self.scratch,
                                                                           filename=filename))

                if not self.config['application']['parameters']['processingmode'] == 'MudPID':
                    f.write(
                        "{PD} -e W{workunitid} ANY \"{workflow}\" -r R{resourceid}\n".format(PD=PDcmd,
                                                                                             workunitid = workunitid,
                                                                                             filename = filename,
                                                                                             resourceid = resouceid,
                                                                                             workflow = PDconfig))

            if self.config['application']['parameters']['processingmode'] == 'MudPID':
                f.write("{PD} -e W{workunitid} ANY \"{workflow}\" -r W{workunitid}\n".format(PD=PDcmd,
                                                                                             workunitid=workunitid,
                                                                                             workflow=PDconfig))

        self.run_commandline("{}\\runme.bat".format(self.scratch), shell_flag = False)

        return True

    def clean(self):
        """
            clean scratch space if no errors
        """
        logger.info("clean is not implemeted yet")
        pass

    @property
    def stage_output(self):
        """
        This function is only for copying PD results!

        TODO(cp@fgcz.ethz.ch): we have distinguish between MudPID and no MudPID

        """

        # fileextpattern = '.*(bat$|csv$|html$|msf$|msfView$|pdAnalysis$|pdResult$|pdResultView$|txt$)'
        fileextpattern = '.*\.(pdResult|csv)$'
        regexfileext = re.compile(fileextpattern)

        relativepath = None

        try:
            regexrelativepath = re.compile(".*(p[1-9]+.*)$")
            match = regexrelativepath.match(self.config['application']['output'][0])

            if match:
                relativepath = os.path.dirname(match.group(1))
        except:
            print("Heuristic for extracting relpath name failed.")
            raise

        workunitid = self.config['job_configuration']['workunit_id']

        for (resourceid, inputfilename) in zip(self.get_resourceids(), self.get_filenames()):
            for item in listdir(self.scratch):
                filename = r"{}\{}".format(self.scratch, item)

                if item.startswith("R{}".format(resourceid)) or item.startswith("W{}".format(workunitid)):
                    src = "{scratchdir}\\{dir}".format(scratchdir=self.scratch, dir=item)
                    print("###", src)
                    dsturl = os.path.dirname(self.config['application']['output'][0])

                    (item_name, item_extension) = os.path.splitext(item)

                    if os.path.isfile(filename) and regexfileext.match(item):
                        dst = "{dsturl}/{filename}{ext}".format(dsturl=dsturl,
                                                                filename = inputfilename,
                                                                ext = item_extension)
                        print("### dst =", dst)
                        if self.scp(src = src, dst = dst,
                                    scp_option=r"-scp -r -i D:\fgcz\id_rsa.ppk"):

                            # successful copies
                            obj = {'workunitid': self.config['job_configuration']['workunit_id'],
                                   'filechecksum': md5(src),
                                   'relativepath': "{relativepath}/{file}".format(relativepath=relativepath, file="{filename}{ext}".format(filename = inputfilename, ext = item_extension)),
                                   'name': "{filename}{ext}".format(filename = inputfilename, ext = item_extension),
                                   'size': os.path.getsize(src),
                                   'status': 'available',
                                   'storageid': 2
                                   }
    
                            res = self.bf.save_object(endpoint='resource', obj=obj)
                            print(res)

                    if os.path.isdir(filename):
                        if self.scp(src = src, dst="{dsturl}/{filename}{ext}".format(dsturl=dsturl,
                                                                                    filename = inputfilename,
                                                                                    ext = item_extension),
                                    scp_option=r"-scp -r -i D:\fgcz\id_rsa.ppk"):

                            # this is a directory
                            obj = {'workunitid': self.config['job_configuration']['workunit_id'],
                                   'filechecksum': "### DIRECTORY ###",
                                   'relativepath': "{relativepath}/{filename}{ext}".format(relativepath=relativepath,
                                                                                           filename = inputfilename,
                                                                                           ext = item_extension),
                                   'name': "DIRECTORY__{item}".format(item = inputfilename),
                                   'size': 0,
                                   'status': 'available',
                                   'storageid': 2
                                   }

                            res = self.bf.save_object(endpoint = 'resource', obj = obj)
                            print(res)

        try:
            print("trying to delete old output resouce ...")
            res = self.bf.delete_object(endpoint='resource', id = self.config['job_configuration']['output']['resource_id'][0])
            print(res)
        except:
            pass

        try:
            print("trying to make workunit available ...")
            res = self.bf.save_object(endpoint='workunit',
                                  obj={'id': workunitid, 'status': 'available'})
            print(res)
        except:
            pass

        return


    def run(self):
        """
            this is the main method of the class
        """

        print(self.config)

        self.create_scratch()
        self.stage_input()
        self.create_pd_workflow_config(targetDir=self.scratch)

        self.run_pd(
            PDconfig="{scratch}\\bfabric.pdProcessingWF;{scratch}\\bfabric.pdConsensusWF".format(scratch=self.scratch))

        self.stage_output()
        # self.clean()

        return True


if __name__ == "__main__":
    parser = OptionParser(usage="usage: %prog -y <yaml formated config file>",
                          version="%prog 1.0")

    parser.add_option("-y", "--yaml",
                      type='string',
                      action="store",
                      dest="yaml_filename",
                      default=None,
                      help="config file.yaml")

    (options, args) = parser.parse_args()

    if not os.path.isfile(options.yaml_filename):
        print("ERROR: no such file '{0}'".format(options.yaml_filename))
        sys.exit(1)
    try:
        with open(options.yaml_filename, 'r') as f:
            content = f.read()
        job_config = yaml.load(content)
        PD = FgczPDWrapper(job_config)
        PD.run()

    except:
        print("ERROR: exit 1")
        raise

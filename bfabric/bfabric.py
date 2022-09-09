#!/usr/bin/env python3
# -*- coding: latin1 -*-

"""

B-Fabric Appliaction Interface using WSDL

The code contains classes for wrapper_creator and submitter.

Ensure that this file is available on the bfabric exec host.

Copyright (C) 2014 - 2019 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.

Authors:
  Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
  Christian Panse <cp@fgcz.ethz.ch>

Licensed under GPL version 3

$Id: bfabric.py 3000 2017-08-18 14:18:30Z cpanse $
$HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/bfabric.py $
$Date: 2017-08-18 16:18:30 +0200 (Fri, 18 Aug 2017) $
$Revision: 3000 $

"""


import yaml
import json
import sys
from pprint import pprint

try:
    from suds.client import Client
    from suds.client import WebFault
except:
    raise

import hashlib
import os
import base64
import datetime
import re
import unittest

import logging.config

logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'verbose': {
            'format': 'DEBUG %(name)s: %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'zeep.transports': {
            'level': 'DEBUG',
            'propagate': True,
            'handlers': ['console'],
        },
    }
})

import bfabric.gridengine as gridengine
import bfabric.slurm as slurm

if (sys.version_info > (3, 0)):
    import http.client
    http.client.HTTPConnection._http_vsn = 10
    http.client.HTTPConnection._http_vsn_str = 'HTTP/1.0'
    pass
else:
    import httplib
    httplib.HTTPConnection._http_vsn = 10
    httplib.HTTPConnection._http_vsn_str = 'HTTP/1.0'


class bfabricEncoder(json.JSONEncoder):
    """
    Implements json encoder for the Bfabric.print_json method  
    """
    def default(self, o):
        try:
            return dict(o)
        except TypeError:
            pass
        else:
            return list(o)
        return JSONEncoder.default(self, o)

class Bfabric(object):
    """
    Implements read and save object methods for BFabric wsdl interface
    """
    def warning(self, msg):
        sys.stderr.write("\033[93m{}\033[0m\n".format(msg))

    def _read_bfabric(self):
        if self.verbose:
            print(("self.bfabricfilename='{}'".format(self.bfabricfilename)))
        if not os.path.isfile(self.bfabricfilename):
            self.warning("could not find '.bfabricrc.py' file in home directory.")
            return

        with open(self.bfabricfilename) as configfile:
            for line in configfile:
                if not re.match("^#", line):
                    A = line.strip().replace("\"", "").replace("'", "").partition('=')
                    if not A[0] in ['_PASSWD', '_LOGIN', '_WEBBASE']:
                        continue
                    if not A[0] in self.bfabricrc:
                        self.bfabricrc[A[0]] = A[2]
                    else:
                        self.warning("while reading {0}. '{1}' is already set."
                            .format(self.bfabricfilename, A[0]))

    def __init__(self, login=None, password=None, webbase=None, externaljobid=None, bfabricrc=None, verbose=False):


        self.verbose = verbose

        self.cl = {}
        self.verbose = False
        self.bflogin = None
        self.bfpassword = None
        self.webbase = 'https://fgcz-bfabric.uzh.ch/bfabric'
        self.bfabricrc = dict()
        self.query_counter = 0
        self.bfabricfilename = os.path.normpath("{0}/{1}"
            .format(os.path.expanduser("~"), ".bfabricrc.py"))

        self._read_bfabric()

        if bfabricrc:
            self.bfabricfilename = bfabricrc

        if '_PASSWD' in list(self.bfabricrc.keys()) and password is None:
            password = self.bfabricrc['_PASSWD']

        if '_LOGIN' in list(self.bfabricrc.keys()) and login is None:
            login = self.bfabricrc['_LOGIN']

        if '_WEBBASE' in list(self.bfabricrc.keys()) and webbase is None:
            self.webbase = self.bfabricrc['_WEBBASE']

        if not login is None:
            self.bflogin = login

        if not password is None:
            self.bfpassword = password

        if not webbase is None:
            self.webbase = webbase

        if not password or not login:
            print ("login or password missing")
            raise

        if self.verbose:
            pprint(self.bfabricrc)

        msg = "\033[93m--- webbase {}; login; {} ---\033[0m\n".format(self.webbase, self.bflogin)

        sys.stderr.write(msg)

    def get_para(self):
        return {'bflogin': self.bflogin, 'webbase': self.webbase}

    def read_object(self, endpoint, obj, login=None, password=None, page=1):
        """
        A generic method which can connect to any endpoint, e.g., workunit, project, order,
        externaljob, etc, and returns the object with the requested id.
        obj is a python dictionary which contains all the attributes of the endpoint 
        for the "query".
        """
        if login is None:
            login = self.bflogin

        if password is None:
            password = self.bfpassword

        if len(login) >= 32:
            raise ValueError("Sorry, login >= 32 characters.") 

        if len(password) != 32:
            raise ValueError("Sorry, password != 32 characters.") 

        self.query_counter = self.query_counter + 1
        QUERY = dict(login=login, page=page, password=password, query=obj)

        try:
            if not endpoint in self.cl:
                self.cl[endpoint] = Client("".join((self.webbase, '/', endpoint, "?wsdl")), cache=None)
        except Exception as e:
            print (e)
            raise

        try:
            QUERYRES = getattr(self.cl[endpoint].service.read(QUERY), endpoint, None)
        except Exception as e:
            print (e)
            raise
        if self.verbose:
            pprint (QUERYRES)

        return QUERYRES

    def save_object(self, endpoint, obj, debug=None):
        """
        same as read_object above but uses the save method.
        """
        self.query_counter = self.query_counter + 1
        QUERY = dict(login=self.bflogin, password=self.bfpassword)
        QUERY[endpoint] = obj

        try:
            if not endpoint in self.cl:
                self.cl[endpoint] = Client("".join((self.webbase, '/', endpoint, "?wsdl")), cache=None)
        except:
            raise


        try:
            if debug is not None:
                return self.cl[endpoint].service.save(QUERY)

            return getattr(self.cl[endpoint].service.save(QUERY), endpoint, None)
        except:
            raise
    
    def checkandinsert_object(self, endpoint, obj, debug=None):
        """
        wsdl method to check iff dependencies are fullfield
        """

        self.query_counter = self.query_counter + 1
        QUERY = dict(login=self.bflogin, password=self.bfpassword)
        QUERY[endpoint] = obj

        try:
            if not endpoint in self.cl:
                self.cl[endpoint] = Client("".join((self.webbase, '/', endpoint, "?wsdl")), cache=None)
        except:
            raise


        try:
            if debug is not None:
                return self.cl[endpoint].service.save(QUERY)

            return getattr(self.cl[endpoint].service.checkandinsert(QUERY), endpoint, None)
        except:
            raise

    def delete_object(self, endpoint, id=None, debug=None):
        """
        same as read_object above but uses the delete method.
        """

        self.query_counter = self.query_counter + 1
        QUERY = dict(login=self.bflogin, password=self.bfpassword, id=id)

        try:
            if not endpoint in self.cl:
                self.cl[endpoint] = Client("".join((self.webbase, '/', endpoint, "?wsdl")), cache=None)
        except:
            raise

        try:
            if debug is not None:
                return self.cl[endpoint].service.delete(QUERY)

            return getattr(self.cl[endpoint].service.delete(QUERY), endpoint, None)
        except:
            raise

    def upload_file(self, filename, workunitid):
        with open(filename, 'rb') as f:
            content = f.read()
        
        resource_base64 = base64.b64encode(content).decode()

        res = self.save_object('resource', {'base64': resource_base64,
            'name': os.path.basename(filename),
            'description': "base64 encoded file",
            'workunitid': workunitid})

        return res
        
    @staticmethod
    def print_json(queryres=None):
        """
        This method prints the query result as returned by ``read_object`` in JSON format.

        Parameter
        ---------

        queryres : the object returned by ``read_object`` method.  
        """
        if queryres is None:
            raise TypeError("print_json() missing 1 required positional argument: please provide the output from read_object as parameter to print_json")

        res = json.dumps(queryres, cls=bfabricEncoder, sort_keys=True, indent=2)
        print(res)

    @staticmethod
    def print_yaml(queryres=None):
        """
        This method prints the query result as returned by ``read_object`` in YAML format.

        Parameter
        ---------

        queryres : the object returned by ``read_object`` method.  
        """
        if queryres is None:
            raise TypeError("print_yaml() missing 1 required positional argument: please provide the output from read_object as parameter to print_yaml")

        res_json = json.dumps(queryres, cls=bfabricEncoder, sort_keys=True)  
        res = yaml.dump(res_json, default_flow_style=False, encoding=None, default_style=None)
        print(res)

    def set_bfabric_credentials(self, login, password):
        self.bflogin = login
        self.bfpassword = password

    def set_bfabric_webbase(self, url):
        self.webbase = url

    def get_sampleid(self, resourceid=None):
        """
        determines the sample_id  of a given resource_id.
        it performs a recursive dfs.
        TODO(cp): check if the method should be implemented using a stack

        :param resourceid:
        :return: (int, int)
        """

        assert isinstance(resourceid, int)

        try:
            resource = self.read_object('resource', obj={'id': resourceid})[0]
        except:
            return (None)

        try:
            workunit = self.read_object(endpoint='workunit', obj={'id': resource.workunit._id})[0]
            return (self.get_sampleid(resourceid=int(workunit.inputresource[0]._id)))
        except:
            self.warning("fetching sampleid of resource.workunitid = {} failed.".format(resource.workunit._id))
            return (None)

class BfabricFeeder(Bfabric):
    """ 
        this class is used for reporting 'resource' status 
    """

    def report_resource(self, resourceid):
        """
        this function determines the 'md5 checksum', 'the file size', 
        and set the status of the resource available.

        this is gonna executed on the storage host 

        """
        res = self.read_object('resource', {'id': resourceid})[0]
        print (res)

        if not hasattr(res, 'storage'):
            return -1

        storage = self.read_object('storage', {'id': res.storage._id})[0]

        filename = "{0}/{1}".format(storage.basepath, res.relativepath)

        if os.path.isfile(filename):
            try:
                fmd5 = hashlib.md5(open(filename, 'rb').read()).hexdigest()
                print ("md5sum ({}) = {}".format(filename, fmd5))

                fsize = int(os.path.getsize(filename)) + 1
                print ("size ({}) = {}".format(filename, fsize))


                return self.save_object('resource', {'id': resourceid,
                                                 'size': fsize,
                                                 'status': 'available',
                                                 'filechecksum': fmd5})
            except:
                print ("computing md5 failed")
                # print ("{} {}".format(Exception, err))
                raise

        return self.save_object('resource', {'id': resourceid, 'status': 'failed'})


class BfabricExternalJob(Bfabric):
    """
    ExternalJobs can use logging.
    if you have a valid externaljobid use this class instead of
    using Bfabric.


    TODO check if an external job id is provided
    """
    externaljobid = None

    def __init__(self, login=None, password=None, externaljobid=None):
        super(BfabricExternalJob, self).__init__(login, password)
        if not externaljobid:
            print("Error: no externaljobid provided.")
            raise
        else:
            self.externaljobid = externaljobid

        print(("BfabricExternalJob externaljobid={}".format(self.externaljobid)))

    def logger(self, msg):
        if self.externaljobid:
            super(BfabricExternalJob, self).save_object('externaljob', {'id': self.externaljobid, 'logthis': str(msg)})
        else:
            print((str(msg)))

    def save_object(self, endpoint, obj, debug=None):
        res = super(BfabricExternalJob, self).save_object(endpoint, obj, debug)
        jsonres = json.dumps(res, cls=bfabricEncoder, sort_keys=True, indent=2)
        self.logger('saved ' + endpoint + '=' + str(jsonres))
        return res

    def get_workunitid_of_externaljob(self):
        print(("DEBUG get_workunitid_of_externaljob self.externaljobid={}".format(self.externaljobid)))
        res = self.read_object(endpoint='externaljob', obj={'id': self.externaljobid})[0]
        print(res)
        print("DEBUG END")
        workunit_id = None
        try:
            workunit_id = res.cliententityid
            print(("workunitid={}".format(workunit_id)))
        except:
            pass
        return workunit_id

    def get_application_name(self):
        workunitid = self.get_workunitid_of_externaljob()
        if workunitid is None:
            raise ValueError("no workunit available for the given externaljobid.")
        workunit = self.read_object(endpoint='workunit', obj={'id': workunitid})[0]
        if workunit is None:
            raise ValueError("ERROR: no workunit available for the given externaljobid.")
        assert isinstance(workunit._id, int)
        application = self.read_object('application', obj={'id': workunit.application._id})[0]
        return application.name.replace(' ', '_')
        

    def get_executable_of_externaljobid(self):
        """ 
        It takes as input an `externaljobid` and fetches the the `executables` 
        out of the bfabric system using wsdl into a file.       
        returns a list of executables. 

        todo: this function should check if base64 is provided or
        just a program.
        """
        workunitid = self.get_workunitid_of_externaljob()
        if workunitid is None:
            return None

        executables = list()
        for executable in self.read_object(endpoint='executable', obj={'workunitid': workunitid}):
            if hasattr(executable, 'base64'):
                executables.append(executable)

        return executables if len(executables) > 0 else None


class BfabricSubmitter():
    """
    the class is used by the submitter which is executed by the bfabric system.
    """
    
    (G, B) =  (None, None)

    workunitid = None
    workunit = None
    parameters = None
    execfilelist = []
    slurm_dict = {"MaxQuant_textfiles_sge" : {'partition': "prx", 'nodelist': "fgcz-r-033", 'memory':"1G"}, 
            "fragpipe" : {'partition': "prx", 'nodelist': "fgcz-r-033", 'memory':"256G"}, 
            "MaxQuant" : {'partition': "maxquant", 'nodelist': "fgcz-r-033", 'memory':"4G"}, 
            "scaffold_generic" : {'partition': "scaffold", 'nodelist': "fgcz-r-033", 'memory':"256G"}, 
            "MSstats dataProcess" : {'partition': "prx", 'nodelist': "fgcz-r-033", 'memory':"64G"}, 
            "MaxQuant_sampleSizeEstimation" : {'partition': "prx", 'nodelist': "fgcz-r-028", 'memory': "2G"}, 
            "ProteomeDiscovererQC" : {'partition': "prx", 'nodelist': "fgcz-r-035", 'memory': "2G"} 
            }

    def __init__(self, login=None, password=None, externaljobid=None,
                 user='*', node="PRX@fgcz-r-018", partition="prx", nodelist="fgcz-r-028", memory="10G", SCHEDULEROOT='/export/bfabric/bfabric/', scheduler="GridEngine"):
        """
        :rtype : object
        """
        self.B = BfabricExternalJob(login=login, password=password, externaljobid=externaljobid)
        self.partition = partition
        self.nodelist = nodelist
        self.memory = memory
        self.SCHEDULEROOT = SCHEDULEROOT
        self.user = user
        self.scheduler = scheduler

        print((self.B.bflogin))
        print((self.B.externaljobid))

        self.workunitid = self.B.get_workunitid_of_externaljob()

        try:
            self.workunit = self.B.read_object(endpoint='workunit', obj={'id': self.workunitid})[0]
        except:
            print ("ERROR: could not fetch workunit while calling constructor in BfabricSubmitter.")
            raise


        try:
            self.parameters = [self.B.read_object(endpoint='parameter', obj={'id': x._id})[0] for x in self.workunit.parameter]
        except:
            self.parameters = list()
            print ("Warning: could not fetch parameter.")

        partition = [x for x in self.parameters if x.key == "partition"]
        nodelist = [x for x in self.parameters if x.key == "nodelist"]
        memory = [x for x in self.parameters if x.key == "memory"]
        application_name = self.B.get_application_name()

        if len(partition) > 0 and len(nodelist) > 0 and len(memory)>0:
            self.partition = partition[0].value
            self.nodelist = nodelist[0].value
            self.memory = memory[0].value
        elif "queue" in [x.key for x in self.parameters] and application_name in self.slurm_dict:
            # Temporary check for old workunit previously run with SGE
            self.partition = self.slurm_dict[application_name]['partition']
            self.nodelist = self.slurm_dict[application_name]['nodelist']
            self.memory = self.slurm_dict[application_name]['memory']
        else:
            pass

        print(("partition={0}".format(self.partition)))
        print(("nodelist={0}".format(self.nodelist)))
        print(("memory={0}".format(self.memory)))
        print("__init__ DONE")


    def submit_gridengine(self, script="/tmp/runme.bash", arguments=""):

        GE = gridengine.GridEngine(user=self.user, queue=self.queue, GRIDENGINEROOT=self.SCHEDULEROOT)

        print(script)
        print((type(script)))
        resQsub = GE.qsub(script=script, arguments=arguments)

        self.B.logger("{}".format(resQsub))


    def submit_slurm(self, script="/tmp/runme.bash", arguments=""):

        SL = slurm.SLURM(user=self.user, SLURMROOT=self.SCHEDULEROOT)

        print(script)
        print((type(script)))
        resSbatch = SL.sbatch(script=script, arguments=arguments)

        self.B.logger("{}".format(resSbatch))


    def compose_bash_script(self, configuration=None, configuration_parser=lambda x: yaml.safe_load(x)):
        """
        composes the bash script which is executed by the submitter (sun grid engine).
        as argument it takes a configuration file, e.g., yaml, xml, json, or whatsoever, and a parser function.

        it returns a str object containing the code.

        :rtype : str
        """


        #assert isinstance(configuration, str)

        try:
            config = configuration_parser(configuration)
        except:
            raise ValueError("error: parsing configuration content failed.")


        _cmd_template = """#!/bin/bash
# Maria d'Errico
# Christian Panse
# 2020-09-28
# 2020-09-29
# https://GitHub.com/fgcz/bfabricPy/
# Slurm
#SBATCH --partition={0}
#SBATCH --nodelist={11}
#SBATCH -n 1
#SBATCH -N 1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu={12}
#SBATCH -e {1}
#SBATCH -o {2}
#SBATCH --job-name=WU{10}
#SBATCH --workdir=/home/bfabric
#SBATCH --export=ALL,HOME=/home/bfabric

# Grid Engine Parameters
#$ -q {0}&{11}
#$ -e {1}
#$ -o {2}


set -e
set -o pipefail

export EMAIL="cp@fgcz.ethz.ch wew@fgcz.ethz.ch maria.derrico@fgcz.ethz.ch"
export EXTERNALJOB_ID={3}
export RESSOURCEID_OUTPUT={4}
export RESSOURCEID_STDOUT_STDERR="{5} {6}"
export OUTPUT="{7}"
export WORKUNIT_ID="{10}"
STAMP=`/bin/date +%Y%m%d%H%M`.$$.$JOB_ID
TEMPDIR="/home/bfabric/prx"

_OUTPUT=`echo $OUTPUT | cut -d"," -f1`
test $? -eq 0 && _OUTPUTHOST=`echo $_OUTPUT | cut -d":" -f1`
test $? -eq 0 && _OUTPUTPATH=`echo $_OUTPUT | cut -d":" -f2`
test $? -eq 0 && _OUTPUTPATH=`dirname $_OUTPUTPATH`
test $? -eq 0 && ssh $_OUTPUTHOST "mkdir -p $_OUTPUTPATH"
test $? -eq 0 && echo $$ > $TEMPDIR/$$
test $? -eq 0 && scp $TEMPDIR/$$ $OUTPUT

if [ $? -eq 1 ];
then
    echo "writting to output url failed!";
    exit 1;
fi

# job configuration set by B-Fabrics wrapper_creator executable
# application parameter/configuration
cat > $TEMPDIR/config_WU$WORKUNIT_ID.yaml <<EOF
{8}
EOF



## interrupt here if you want to do a semi-automatic processing
if [ -x /usr/bin/mutt ];
then
    cat $0 > $TEMPDIR/$JOB_ID.bash 

    (who am i; hostname; uptime; echo $0; pwd; ps;) \
    | mutt -s "JOB_ID=$JOB_ID WORKUNIT_ID=$WORKUNIT_ID EXTERNALJOB_ID=$EXTERNALJOB_ID" $EMAIL \
        -a $TEMPDIR/$JOB_ID.bash $TEMPDIR/config_WU$WORKUNIT_ID.yaml 
fi
# exit 0

# run the application
test -f $TEMPDIR/config_WU$WORKUNIT_ID.yaml && {9} $TEMPDIR/config_WU$WORKUNIT_ID.yaml


if [ $? -eq 0 ];
then
     ssh fgcz-r-035.uzh.ch "bfabric_setResourceStatus_available.py $RESSOURCEID_OUTPUT" \
     | mutt -s "JOB_ID=$JOB_ID WORKUNIT_ID=$WORKUNIT_ID EXTERNALJOB_ID=$EXTERNALJOB_ID DONE" $EMAIL 

     bfabric_setExternalJobStatus_done.py $EXTERNALJOB_ID
     bfabric_setWorkunitStatus_available.py $WORKUNIT_ID
    echo $?
else
    echo "application failed"
     mutt -s "JOB_ID=$JOB_ID WORKUNIT_ID=$WORKUNIT_ID EXTERNALJOB_ID=$EXTERNALJOB_ID failed" $EMAIL < /dev/null
     bfabric_setResourceStatus_available.py $RESSOURCEID_STDOUT_STDERR $RESSOURCEID;
    exit 1;
fi

# should be available also as zero byte files
bfabric_setResourceStatus_available.py $RESSOURCEID_STDOUT_STDERR


exit 0
""".format(self.partition,
               config['job_configuration']['stderr']['url'],
               config['job_configuration']['stdout']['url'],
               config['job_configuration']['external_job_id'],
               config['job_configuration']['output']['resource_id'],
               config['job_configuration']['stderr']['resource_id'],
               config['job_configuration']['stdout']['resource_id'],
               ",".join(config['application']['output']),
               configuration,
               config['job_configuration']['executable'],
               config['job_configuration']['workunit_id'],
               self.nodelist,
               self.memory)

        return _cmd_template


    def submitter_yaml(self):
        """
        implements the default submitter

        the function fetches the yaml base64 configuration file linked to the external job id out of the B-Fabric
        system. Since the file can not be stagged to the LRMS as argument, we copy the yaml file into the bash script
        and stage it on execution the application.

        TODO(cp): create the output url before the application is started.

        return None
        """

        # foreach (executable in external job):
        for executable in self.B.get_executable_of_externaljobid():
            self.B.logger("executable = {0}".format(executable))

            try:
                content = base64.b64decode(executable.base64.encode()).decode()
            except:
                raise ValueError("error: decoding executable.base64 failed.")


            print(content)
            _cmd_template = self.compose_bash_script(configuration=content,
                                                     configuration_parser=lambda x: yaml.safe_load(x))

            _bash_script_filename = "/home/bfabric/prx/workunitid-{0}_externaljobid-{1}_executableid-{2}.bash"\
                .format(self.B.get_workunitid_of_externaljob(), self.B.externaljobid, executable._id)

            with open(_bash_script_filename, 'w') as f:
                f.write(_cmd_template)
            
            if self.scheduler=="GridEngine" :
                self.submit_gridengine(_bash_script_filename)
            else: 
                self.submit_slurm(_bash_script_filename)
            self.execfilelist.append(_bash_script_filename)


        res = self.B.save_object(endpoint='externaljob',
                                obj={'id': self.B.externaljobid, 'status': 'done'})
    def get_job_script(self):
        return self.execfilelist


class BfabricWrapperCreator(BfabricExternalJob):
    """
    the class is used for the wrapper_creator which is executed by the bfabtic system
    (non batch) so each resource is processed seperate
    """

    (externaljobid_submitter, workunit_executableid) = (None, None)

    def get_externaljobid_yaml_workunit(self):
        return self.externaljobid_yaml_workunit

    def uploadGridEngineScript(self, para={'INPUTHOST': 'fgcz-r-035.uzh.ch'}):
        """
        the methode creates and uploads an executebale.  
        """

        self.warning(
            "This python method is superfluously and will be removed. Please use the write_yaml method of the BfabricWrapperCreato class.")

        _cmd_template = """#!/bin/bash
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/bfabric.py $
# $Id: bfabric.py 3000 2017-08-18 14:18:30Z cpanse $
# Christian Panse <cp@fgcz.ethz.ch>
#$ -q PRX@fgcz-r-028
#$ -e {1}
#$ -o {2}

set -e
set -o pipefail


# debug
hostname
uptime
echo $0
pwd

# variables to be set by the wrapper_creator executable
{0}


# create output directory
ssh $SSHARGS $OUTPUTHOST "mkdir -p $OUTPUTPATH" || exit 1

# staging input and output data and proc
ssh $SSHARGS $INPUTHOST "cat $INPUTPATH/$INPUTFILE" \\
| $APPLICATION --inputfile $INPUTFILE --ssh "$OUTPUTHOST:$OUTPUTPATH/$OUTPUTFILE" \\
&& bfabric_setResourceStatus_available.py $RESSOURCEID \\
&& bfabric_setExternalJobStatus_done.py $EXTERNALJOBID \\
|| exit 1

exit 0
""".format("\n".join(sorted(['%s="%s"' % (key, info) for key, info in para.iteritems()])), para['STDERR'],
           para['STDOUT'])

        resExecutable = self.save_object('executable', {'name': os.path.basename(para['APPLICATION']) + "_executable",
                                                        'context': 'WORKUNIT',
                                                        'parameter': None,
                                                        'description': "This script should run as 'bfabric' user in the FGCZ compute infrastructure.",
                                                        'workunitid': para['WORKUNITID'],
                                                        'base64': base64.b64encode(_cmd_template),
                                                        'version': 0.2})

        return (resExecutable)

    def get_executableid(self):
        return (self.workunit_executableid)

    def write_yaml(self,  data_serializer=lambda x: yaml.dump(x, default_flow_style=False, encoding=None)):
        """
        This method writes all related parameters into a yaml file which is than upload as base64 encoded
        file into the b-fabric system.

        if the method does not excepted at the end it reports also the status of the external_job.

        TODO(cp): make this function more generic so that it can also export xml, json, yaml, ...
        """

        # Inherits all parameters of the application executable out of B-Fabric to create an executable script
        workunitid = self.get_workunitid_of_externaljob()

        if workunitid is None:
            raise ValueError("no workunit available for the given externaljobid.")

        workunit = self.read_object(endpoint='workunit', obj={'id': workunitid})[0]
        if workunit is None:
            raise ValueError("ERROR: no workunit available for the given externaljobid.")

        assert isinstance(workunit._id, int)

        application = self.read_object('application', obj={'id': workunit.application._id})[0]
        # TODO(cp): rename to application_execuatbel
        workunit_executable = self.read_object('executable', obj={'id': workunit.applicationexecutable._id})[0]
        try:
            self.workunit_executableid = workunit_executable._id
        except:
            self.workunit_executableid = None

        # Get container details
        container = workunit.container
        fastasequence = ""
        if container._classname=="order":
            order = self.read_object('order', obj={'id': container._id})[0]
            order_id = order._id
            if "project" in order:
                project_id = order.project._id
            else:
                project_id = None
            if "fastasequence" in order:
                fastasequence = "\n".join([x.strip() for x in str(order.fastasequence).split("\r")])
        else:
            order_id = None
            project_id = container._id

        today = datetime.date.today()

        # merge all information into the executable script
        _output_storage = self.read_object('storage', obj={'id': application.storage._id})[0]

        _output_relative_path = "p{0}/bfabric/{1}/{2}/{3}/workunit_{4}/".format(
            container._id,
            application.technology.replace(' ', '_'),
            application.name.replace(' ', '_'),
            today.strftime('%Y/%Y-%m/%Y-%m-%d/'),
            workunitid)

        # Setup the log_storage to SlurmLog with id 13
        _log_storage = self.read_object('storage', obj={'id': 13})[0]

        #_cmd_applicationList = [workunit_executable.program]

        application_parameter = {}

        if not getattr(workunit, "parameter", None) is None:
            for para in workunit.parameter:
                parameter = self.read_object('parameter', obj={'id': para._id})
                if parameter:
                    for p in parameter:
                        try:
                            application_parameter["{}".format(p.key)] = "{}".format(p.value)
                        except:
                            application_parameter["{}".format(p.key)] = ""

        try:
            input_resources = [x._id for x in workunit.inputresource]
            input_resources = [self.read_object(endpoint='resource', obj={'id': x})[0] for x in input_resources]
        except:
            print("no input resources found. continue with empty list.")
            input_resources = []


        # query all urls and ids of the input resources
        resource_urls = dict()
        resource_ids = dict()

        for resource_iterator in input_resources:
            try:
                _appication_id = self.read_object(endpoint='workunit',
                                               obj={'id': resource_iterator.workunit._id})[0].application._id

                _application_name = "{0}".format(self.read_object('application', obj={'id': _appication_id})[0].name)

                _storage = self.read_object('storage', {'id': resource_iterator.storage._id})[0]

                _inputUrl = "bfabric@{0}:/{1}/{2}".format(_storage.host, _storage.basepath, resource_iterator.relativepath)

                if not _application_name in resource_urls:
                    resource_urls[_application_name] = []
                    resource_ids[_application_name] = []

                resource_urls[_application_name].append(_inputUrl)

                sample_id = self.get_sampleid(int(resource_iterator._id))

                _resource_sample = {'resource_id': int(resource_iterator._id),
                                        'resource_url': "{0}/userlab/show-resource.html?id={1}".format(self.webbase,resource_iterator._id)}


                if not sample_id is None:
                    _resource_sample['sample_id'] = int(sample_id)
                    _resource_sample['sample_url'] = "{0}/userlab/show-sample.html?id={1}".format(self.webbase, sample_id)

                resource_ids[_application_name].append(_resource_sample)
            except:
                print ("resource_iterator failed. continue ...")
                pass


        # create resources for output, stderr, stdout
        _ressource_output = self.save_object('resource', {
            'name': "{0} {1} - resource".format(application.name, len(input_resources)),
            'workunitid': workunit._id,
            'storageid': int(application.storage._id),
            'relativepath': _output_relative_path})[0]


        print(_ressource_output)
        _output_filename = "{0}.{1}".format(_ressource_output._id, application.outputfileformat)
        # we want to include the resource._id into the filename
        _ressource_output = self.save_object('resource',
                                    {'id': int(_ressource_output._id),
                                     'relativepath': "{0}/{1}".format(_output_relative_path, _output_filename)})[0]

        print (_ressource_output)
        _resource_stderr = self.save_object('resource', {
            'name': 'slurm_stderr',
            'workunitid': int(workunit._id),
            'storageid': _log_storage._id,
            'relativepath': "/workunitid-{0}_resourceid-{1}.err".format(workunit._id, _ressource_output._id)})[0]

        _resource_stdout = self.save_object('resource', {
            'name': 'slurm_stdout',
            'workunitid': workunit._id,
            'storageid': _log_storage._id,
            'relativepath': "/workunitid-{0}_resourceid-{1}.out".format(workunit._id, _ressource_output._id)})[0]


        # Creates the workunit executable
        # The config includes the externaljobid: the yaml_workunit_externaljob has to be created before it.
        # The yaml_workunit_externaljob cannot be created without specifying an executableid:
        # a yaml_workunit_executable is thus created before the config definition in order to provide
        # the correct executableid to the yaml_workunit_externaljob.
        # However this yaml_workunit_executable has to be updated later to include 'base64': base64.b64encode(config_serialized.encode()).decode()  
        yaml_workunit_executable = self.save_object('executable', {'name': 'job configuration (executable) in YAML',
                       'context': 'WORKUNIT',
                       'workunitid': workunit._id,
                       'description': "This is a job configuration as YAML base64 encoded. It is configured to be executed by the B-Fabric yaml submitter."})[0]
        print(yaml_workunit_executable)
        
        yaml_workunit_externaljob = self.save_object('externaljob',
                                                    {"workunitid": workunit._id, 
                                                    'status': 'new',
                                                    'executableid' : yaml_workunit_executable._id, 
                                                    'action': "WORKUNIT"})[0]
        print(yaml_workunit_externaljob)
        assert isinstance(yaml_workunit_externaljob._id, int)
        self.externaljobid_yaml_workunit = int(yaml_workunit_externaljob._id)
        print(("XXXXXXX self.externaljobid_yaml_workunit ={} XXXXXXX".format(self.externaljobid_yaml_workunit)))

        _output_url = "bfabric@{0}:{1}{2}/{3}".format(_output_storage.host,
                                                    _output_storage.basepath,
                                                    _output_relative_path,
                                                    _output_filename)

        try:
            query_obj = {'id': workunit.inputdataset._id}
            inputdataset = self.read_object(endpoint='dataset', obj=query_obj)[0]
            inputdataset_json = json.dumps(inputdataset, cls=bfabricEncoder, sort_keys=True, indent=2)
            inputdataset = json.loads(inputdataset_json)
        except:
            inputdataset = None

        # Compose configuration structure
        config = {
            'job_configuration': {
                'executable': "{}".format(workunit_executable.program),
                'inputdataset': inputdataset,
                'input': resource_ids,
                'output': {
                    'protocol': 'scp',
                    'resource_id': int(_ressource_output._id),
                    'ssh_args': "-o StrictHostKeyChecking=no -2 -l bfabric -x"
                },
                'stderr': {
                        'protocol': 'file',
                        'resource_id': int(_resource_stderr._id) ,
                        'url': "{0}/workunitid-{1}_resourceid-{2}.err".format(_log_storage.basepath, workunit._id, _ressource_output._id)
                    },
                'stdout': {
                        'protocol': 'file',
                        'resource_id': int(_resource_stdout._id),
                        'url': "{0}/workunitid-{1}_resourceid-{2}.out".format(_log_storage.basepath, workunit._id, _ressource_output._id)
                    },
                'workunit_id': int(workunit._id),
                'workunit_url': "{0}/userlab/show-workunit.html?workunitId={1}".format(self.webbase, workunit._id),
                'external_job_id': int(yaml_workunit_externaljob._id),
                'order_id': order_id,
                'project_id': project_id,
                'fastasequence': fastasequence
            },
            'application' : {
                'protocol': 'scp',
                'parameters': application_parameter,
                'input': resource_urls,
                'output': [_output_url]
            }
        }

        config_serialized = data_serializer(config)
        print(config_serialized)

        yaml_workunit_executable = self.save_object('executable', {'id': yaml_workunit_executable._id,
                                                        'base64': base64.b64encode(config_serialized.encode()).decode(),
                                                        'version': "{}".format(10)})[0]
        print(yaml_workunit_executable)

        # The WrapperCreator executable is successful, and the status of the its external job is set to done,
        # which triggers B-Fabric to create an external job for the submitter executable.

        wrapper_creator_externaljob = self.save_object(endpoint='externaljob',
                                                       obj={'id': self.externaljobid, 'status': 'done'})

        print(("\n\nquery_counter={0}".format(self.query_counter)))




if __name__ == "__main__":
    bfapp = Bfabric(verbose=True)

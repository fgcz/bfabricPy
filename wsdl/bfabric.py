#!/usr/bin/python

# -*- coding: latin1 -*-

"""

B-Fabric Appliaction Interface using WSDL

The code contains classes for wrapper_creator and submitter.

Ensure that this file is available on the bfabric exec host.

"""

# Copyright (C) 2014, 2015 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Marco Schmidt <marco.schmidt@fgcz.ethz.ch>
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3

# $Id: bfabric.py 1954 2015-09-02 14:38:16Z cpanse $
#
# $HeadURL: http://fgcz-svn/repos/scripts/trunk/linux/bfabric/apps/python/bfabric.py $
#
# $Date: 2015-09-02 16:38:16 +0200 (Wed, 02 Sep 2015) $
import yaml

import sys

try:
    from suds.client import Client
except:
    sys.exit(1)

import hashlib
import os
import base64
import datetime
import re

import gridengine


class Bfabric(object):
    """
    Implements read and save object methods for BFabric wsdl interface
    """
    bflogin = 'pfeeder'
    bfpassword = 'XXXXXXXX'
    webbase = 'http://fgcz-bfabric.uzh.ch/bfabric'
    bfabricrc = dict()

    def _read_bfabric(self):
        bfabricfilename = os.environ['HOME'] + "/.bfabricrc.py"

        if not os.path.isfile(bfabricfilename):
            return
        try:
            with open(bfabricfilename) as myfile:
                for line in myfile:
                    if not re.match("^#", line):
                        A = line.strip().replace("\"", "").replace("'", "").partition('=')
                        self.bfabricrc[A[0]] = A[2]
        except:
            raise

    def __init__(self, login=None, password=None, externaljobid=None):
        self._read_bfabric()

        if '_PASSWD' in self.bfabricrc.keys():
            password = self.bfabricrc['_PASSWD']

        if '_LOGIN' in self.bfabricrc.keys():
            login = self.bfabricrc['_LOGIN']

        if '_WEBBASE' in self.bfabricrc.keys():
            self.webbase = self.bfabricrc['_WEBBASE']

        if login:
            self.bflogin = login
        if password:
            self.bfpassword = password

        if not password or not login:
            print ("login or password missing")
            sys.exit(1)

    # TODO do a test if the login is working

    def read_object(self, endpoint, obj):
        """
        A generic methode which can connect to any endpoint, e.g., workunit, project,
        externaljob, etc, and returns the object with the requested id.
        obj is a python dictionary which contains all the attributes of the endpoint 
        for the "query".
        """
        QUERY = dict(login=self.bflogin, password=self.bfpassword, query=obj)
        try:
            client = Client("".join((self.webbase, '/', endpoint, "?wsdl")))
        except suds.WebFault, e:
            print e

        # print client.service.read(QUERY)
        return getattr(client.service.read(QUERY), endpoint, None)

    def save_object(self, endpoint, obj, debug=None):
        """
        same as read_object above but uses the save method.
        """
        QUERY = dict(login=self.bflogin, password=self.bfpassword)
        QUERY[endpoint] = obj

        try:
            client = Client("".join((self.webbase, '/', endpoint, "?wsdl")))
        except suds.WebFault, e:
            print e

        if debug is not None:
            return client.service.save(QUERY)

        return getattr(client.service.save(QUERY), endpoint, None)

    def delete_object(self, endpoint, id=None, debug=None):
        """
        same as read_object above but uses the delete method.
        """

        QUERY = dict(login=self.bflogin, password=self.bfpassword, id=id)

        try:
            client = Client("".join((self.webbase, '/', endpoint, "?wsdl")))
        except suds.WebFault, e:
            print e

        if debug is not None:
            return client.service.delete(QUERY)

        return getattr(client.service.delete(QUERY), endpoint, None)

    def set_bfabric_credentials(self, login, password):
        self.bflogin = login
        self.bfpassword = password

    def set_bfabric_webbase(self, url):
        self.webbase = url


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

        if not hasattr(res, 'storage'):
            return -1

        storage = self.read_object('storage', {'id': res.storage._id})[0]

        filename = "{0}/{1}".format(storage.basepath, res.relativepath)

        if os.path.isfile(filename):
            return self.save_object('resource', {'id': resourceid,
                                                 'size': os.path.getsize(filename),
                                                 'status': 'available',
                                                 'filechecksum': hashlib.md5(open(filename, 'rb').read()).hexdigest()})

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
            print "Error: no externaljobid provided."
            sys.exit(1)
        else:
            self.externaljobid = externaljobid

    def logger(self, msg):
        if self.externaljobid:
            super(BfabricExternalJob, self).save_object('externaljob', {'id': self.externaljobid, 'logthis': str(msg)})
        else:
            print str(msg)

    def save_object(self, endpoint, obj, debug=None):
        res = super(BfabricExternalJob, self).save_object(endpoint, obj, debug)
        self.logger('saved ' + endpoint + '=' + str(res))
        return res

    def get_workunitid_of_externaljob(self):
        res = self.read_object('externaljob', {'id': self.externaljobid})[0]
        workunit_list = filter(lambda x: x[0] == 'cliententityid', res)
        return workunit_list[0][1] if workunit_list else None

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


class BfabricSubmitter(BfabricExternalJob, gridengine.GridEngine):
    """
    the class is used by the submitter which is executed by the bfabric system.
    """

    def __init__(self, login=None, password=None, externaljobid=None,
                 user='*', queue="PRX@fgcz-c-071", GRIDENGINEROOT='/usr/local/GE2011'):
        """

        :rtype : object
        """
        gridengine.GridEngine.__init__(self, user=user, queue=queue, GRIDENGINEROOT=GRIDENGINEROOT)
        BfabricExternalJob.__init__(self, login=login, password=password, externaljobid=externaljobid)

    def submit(self, script, arguments=""):

        resQsub = super(BfabricSubmitter, self).qsub(script, arguments)
        self.logger(resQsub)

    def compose_bash_script(self, yaml_content=None):
        if yaml_content is None:
            print "no yaml content provided."
            sys.exit(1)

        assert isinstance(yaml_content, str)

        try:
            config = yaml.load(yaml_content)
        except:
            print "error: parsing yaml content failed."
            sys.exit(1)


        _cmd_template = """#!/bin/bash
#
# $HeadURL: http://fgcz-svn/repos/scripts/trunk/linux/bfabric/apps/python/bfabric.py $
# $Id: bfabric.py 1954 2015-09-02 14:38:16Z cpanse $
# Christian Panse <cp@fgcz.ethz.ch> 2007-2015

# Grid Engine Parameters
#$ -q {0}
#$ -e {1}
#$ -o {2}


set -e
set -o pipefail

export EXTERNALJOBID={3}
export RESSOURCEID_OUTPUT={4}
export RESSOURCEID_STDOUT_STDERR="{5} {6}"
export OUTPUT="{7}"

# job configuration set by B-Fabrics wrapper_creator executable
_OUTPUT=`echo $OUTPUT | cut -d"," -f1`
test $? -eq 0 && _OUTPUTHOST=`echo $_OUTPUT | cut -d":" -f1`
test $? -eq 0 && _OUTPUTPATH=`echo $_OUTPUT | cut -d":" -f2`
test $? -eq 0 && _OUTPUTPATH=`dirname $_OUTPUTPATH`
test $? -eq 0 && ssh $_OUTPUTHOST "mkdir -p $_OUTPUTPATH"

if [ $? -eq 1 ];
then
    echo "writting to output url failed!";
    exit 1;
fi

cat > /tmp/yaml_config.$$ <<EOF
{8}
EOF

# debug / host statistics
hostname
uptime
echo $0
pwd

# run the application
test -f /tmp/yaml_config.$$ && {9} /tmp/yaml_config.$$

if [ $? -eq 0 ];
then
    /home/bfabric/.python/fgcz_bfabric_setResourceStatus_available.py $RESSOURCEID_OUTPUT
    /home/bfabric/.python/fgcz_bfabric_setExternalJobStatus_done.py $EXTERNALJOBID
else
    echo "application failed"
    /home/bfabric/.python/fgcz_bfabric_setResourceStatus_available.py $RESSOURCEID_STDOUT_STDERR $RESSOURCEID;
    exit 1;
fi


# should be available also as zero byte files

/home/bfabric/.python/fgcz_bfabric_setResourceStatus_available.py $RESSOURCEID_STDOUT_STDERR


exit 0
""".format(self.queue,
               config['job_configuration']['stderr']['url'],
               config['job_configuration']['stdout']['url'],
               config['job_configuration']['external_job_id'],
               config['job_configuration']['output']['resource_id'],
               config['job_configuration']['stderr']['resource_id'],
               config['job_configuration']['stdout']['resource_id'],
               ",".join(job_config['application']['output']),
               yaml_content,
               config['job_configuration']['executable'])

        return _cmd_template

    def submitter_yaml(self):
        """
        implements the default submitter

        the function feches the yaml base64 configuration file linked to the external job id out of the B-Fabric
        system. Since the file can not be staged to the LRMS as argument we copy the yaml file into the bash script
        and stage it on execution the the application.


        TODO(cp): create the output url before the application is started.


        return None
        """

        # foreach (executable in externaljob):
        for executable in self.get_executable_of_externaljobid():
            self.logger("executable = {0}".format(executable))


            try:
                yaml_content = base64.b64decode(executable.base64)
            except:
                print "error: decoding executable.base64 failed."
                sys.exit(1)


            _cmd_template = compose_bash_script(yaml_content)


            _bash_script_filename = "/tmp/externaljobid-{0}_executableid-{1}.bash".format(self.externaljobid,
                                                                                          executable._id)

            with open(_bash_script_filename, 'w') as f:
                f.write(_cmd_template)

            self.submit(_bash_script_filename)

        res = self.save_object(endpoint='externaljob',
                                obj={'id': self.externaljobid, 'status': 'done'})



class BfabricWrapperCreator(BfabricExternalJob):
    """
    the class is used for the wrapper_creator which is executed by the bfabtic system
    (non batch) so each resource is processed seperate
    """

    def uploadGridEngineScript(self, para={'INPUTHOST': 'fgcz-s-021.uzh.ch'}):
        """
        the methode creates and uploads an executebale.  
        """
        _cmd_template = """#!/bin/bash
# $HeadURL: http://fgcz-svn/repos/scripts/trunk/linux/bfabric/apps/python/bfabric.py $
# $Id: bfabric.py 1954 2015-09-02 14:38:16Z cpanse $
# Christian Panse <cp@fgcz.ethz.ch>
#$ -q PRX@fgcz-c-071
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
&& /home/bfabric/.python/fgcz_bfabric_setResourceStatus_available.py $RESSOURCEID \\
&& /home/bfabric/.python/fgcz_bfabric_setExternalJobStatus_done.py $EXTERNALJOBID \\
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

    def uploadGridEngineScriptNonBatch(self, para={'INPUTHOST': 'fgcz-s-021.uzh.ch'}):
        """
        the methode creates and uploads an executebale.  
        """
        _cmd_template0 = """#!/bin/bash
# $HeadURL: http://fgcz-svn/repos/scripts/trunk/linux/bfabric/apps/python/bfabric.py $
# $Id: bfabric.py 1954 2015-09-02 14:38:16Z cpanse $
# Christian Panse <cp@fgcz.ethz.ch>
#$ -q PRX@fgcz-c-071
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

INPUTURLS={3}

export RESSOURCEID
export INPUTURLS
export INPUTRESOURCEID
""".format("\n".join(sorted(['%s="%s"' % (key, info) for key, info in para.iteritems()])), para['STDERR'],
           para['STDOUT'], para['INPUTURLS'])

        _cmd_template1 = """
# create output directory
ssh $SSHARGS $OUTPUTHOST "mkdir -p $OUTPUTPATH" || exit 1
test $? -eq 0 || exit 1

SCRATCH=/scratch/$JOB_ID/


mkdir -p $SCRATCH
test $? -eq 0 || exit 1

echo "BEGIN COPY INPUT"
for (( i=0; ; i++ ))
do
    test -z "${INPUTURLS[$i]}" && break
    # TODO(cp@fgcz.ethz.ch): This is pain of the art.
    echo "${INPUTURLS[$i]}" >> $SCRATCH/inputurl.txt
    scp -c arcfour  ${INPUTURLS[$i]} $SCRATCH/`basename ${INPUTURLS[$i]}`
    test $? -eq 0 || { echo "scp failed with '${INPUTURLS[$i]}'"; exit 1; }
done
echo "END COPY INPUT"


$APPLICATION --scratch "$SCRATCH" --ssh "$OUTPUTHOST:$OUTPUTPATH/$OUTPUTFILE" --workunit "$WORKUNITID" \\
&& /home/bfabric/.python/fgcz_bfabric_setResourceStatus_available.py $RESSOURCEID \\
&& /home/bfabric/.python/fgcz_bfabric_setExternalJobStatus_done.py $EXTERNALJOBID \\
|| { echo "application failed"; /home/bfabric/.python/fgcz_bfabric_setResourceStatus_available.py $RESSOURCEID; exit 1; }

cd $SCRATCH && rm -rf ./* \
|| { echo "clean failed"; exit 1; }

exit 0
"""

        resExecutable = self.save_object('executable', {'name': os.path.basename(para['APPLICATION']) + "_executable",
                                                        'context': 'WORKUNIT',
                                                        'parameter': None,
                                                        'description': "This script should run as 'bfabric' user in the FGCZ compute infrastructure.",
                                                        'workunitid': para['WORKUNITID'],
                                                        'base64': base64.b64encode(_cmd_template0 + _cmd_template1),
                                                        'version': 0.3})

        return (resExecutable)

    def write_yaml(self):
        """
        This method writes all related parameters into a yaml file which is than upload as base64 encoded
        file into the b-fabric system.

        if the method does not excepted at the end it reports also the status of the external_job.

        TODO(cp): make this function more generic so that it can also export xml, json, yaml, ...
        """


        workunitid = self.get_workunitid_of_externaljob()

        if workunitid is None:
            print "ERROR: no workunit available for the given externaljobid."
            sys.exit(1)

        workunit = self.read_object(endpoint='workunit', obj={'id': workunitid})
        if workunit is None:
            print "ERROR: no workunit available for the given externaljobid."
            sys.exit(1)

        # collects all required information out of B-Fabric to create an executable script
        workunit = workunit[0]
        application = self.read_object('application', obj={'id': workunit.application._id})[0]
        executable = self.read_object('executable', obj={'id': workunit.applicationexecutable._id})[0]
        project = workunit.project
        today = datetime.date.today()


        # merge all information into the executable script
        _outputStorage = self.read_object('storage', obj={'id': application.storage._id})[0]

        _outputRelativePath = "/p{0}/bfabric/{1}/{2}/{3}/workunit_{4}/".format(
            project._id,
            application.technology.replace(' ', '_'),
            application.name.replace(' ', '_'),
            today.strftime('%Y/%Y-%m/%Y-%m-%d/'),
            workunitid)

        _logStorage = self.read_object('storage', obj={'id': 7})[0]

        _cmd_applicationList = [executable.program]

        application_parameter = {}

        if not getattr(workunit, "parameter", None) is None:
            for parameter in workunit.parameter:
                parameter = self.read_object('parameter', obj={'id': parameter._id, 'context': 'APPLICATION'})
                if parameter:
                    for p in parameter:
                        application_parameter["{}".format(p.key)] = "{}".format(p.value)




        resource = map(lambda x: x._id, workunit.inputresource)
        resource = map(lambda x: self.read_object(endpoint='resource', obj={'id': x})[0], resource)
        workunit_id = map(lambda x: x.workunit._id, resource)


        # query all urls and ids of the input resources
        resource_url = dict()
        resource_id = dict()

        for resource_iterator in resource:
            _appication_id  = self.read_object(endpoint='workunit',
                                               obj={'id': resource_iterator.workunit._id})[0].application._id
            _application_name = "{0}".format(self.read_object('application', obj={'id': _appication_id})[0].name)
            _storage = self.read_object('storage', {'id': resource_iterator.storage._id})[0]
            _inputUrl = "bfabric@{0}/{1}:/{2}".format(_storage.host, _storage.basepath, resource_iterator.relativepath)
            #_resource_id = "{0}".format(resource_iterator._id)
            _resource_id = int(resource_iterator._id)

            if not _application_name in resource_url:
                resource_url[_application_name] = []
                resource_id[_application_name] = []

            resource_url[_application_name].append(_inputUrl)
            resource_id[_application_name].append(_resource_id)

        # create output resource
        res0 = self.save_object('resource', {
            'name': "{0} {1} - resource".format(application.name, len(resource)),
            'workunitid': workunit._id,
            'storageid': application.storage._id,
            'relativepath': _outputRelativePath})[0]

        try:
            _outputFilename = "{0}.{1}".format(res0._id, application.outputfileformat)
            _gridengine_err_file = "/workunitid-{0}_resourceid-{1}.err".format(workunit._id, res0._id)
            _gridengine_out_file = "/workunitid-{0}_resourceid-{1}.out".format(workunit._id, res0._id)
        except:
            _outputFilename = "{0}.{1}".format(None, application.outputfileformat)
            _gridengine_err_file = "/workunitid-{0}_resourceid-{1}.err".format(workunit._id, None)
            _gridengine_out_file = "/workunitid-{0}_resourceid-{1}.out".format(workunit._id, None)

        _res_err = self.save_object('resource', {
            'name': 'grid_engine_stderr',
            'workunitid': workunit._id,
            'storageid': _logStorage._id,
            'relativepath': _gridengine_err_file})[0]

        _res_out = self.save_object('resource', {
            'name': 'grid_engine_stdout',
            'workunitid': workunit._id,
            'storageid': _logStorage._id,
            'relativepath': _gridengine_out_file})[0]

        resNewExternaljob0 = \
            self.save_object('externaljob', {"workunitid": workunit._id, 'status': 'new', 'action': "WORKUNIT"})[0]
        try:
            resNewExternaljob0_id = resNewExternaljob0._id
        except:
            resNewExternaljob0_id = 0

        try:
            res1 = self.save_object('resource',
                                    {'id': res0._id, 'relativepath': _outputRelativePath + '/' + _outputFilename})
        except:
            res1 = self.save_object('resource',
                                    {'id': None, 'relativepath': _outputRelativePath + '/' + _outputFilename})

        try:
            res0_id = res0._id
            _res_err_id = _res_err._id
            _res_out_id = _res_out._id
        except:
            res0_id = 0
            _res_err_id = 0
            _res_out_id = 0


        _output_url = "bfabric@{0}:{1}{2}/{3}".format(_outputStorage.host,
                                                    _outputStorage.basepath,
                                                    _outputRelativePath,
                                                    _outputFilename)
        # compose configuration structure
        config = {
            'job_configuration': {
                'executable': "{}".format(executable.program),
                'input': resource_id,
                'output': {
                    'protocol': 'scp',
                    'resource_id': int(_res_out_id),
                    'ssh_args': "-o StrictHostKeyChecking=no -c arcfour -2 -l bfabric -x"
                },
                'stderr': {
                        'protocol': 'file',
                        'resource_id': int(_res_err_id) ,
                        'url': "{}{}".format(_logStorage.basepath, _gridengine_err_file)
                    },
                'stdout': {
                        'protocol': 'file',
                        'resource_id': int(_res_out_id),
                        'url': "{}{}".format(_logStorage.basepath, _gridengine_out_file)
                    },
                'workunit_id': int(workunit._id),
                'external_job_id': int(resNewExternaljob0_id)
            },
            'application' : {
                'protocol': 'scp',
                'parameters': application_parameter,
                'input': resource_url,
                'output': [_output_url]
            }
        }

        yaml_config = yaml.dump(config, default_flow_style=False, encoding=None)
        print yaml_config

        yaml_executable = self.save_object('executable', {'name': 'yaml',
                                                        'context': 'WORKUNIT',
                                                        'parameter': None,
                                                        'description': "This is a yaml job configuration file base64 encoded."
                                                                       "It should be executed bu the B-Fabric yaml"
                                                                       "submitter.",
                                                        'workunitid': workunit._id,
                                                        'base64': base64.b64encode(yaml_config),
                                                        'version': 0.2})[0]


        resNewExternaljob1 = self.save_object('externaljob',
                                              {"id": resNewExternaljob0._id,
                                               'executableid': yaml_executable._id})

        resExternaljob = self.save_object(endpoint='externaljob', obj={'id': self.externaljobid,
                                                                       'status': 'done'})

if __name__ == "__main__":
    example_yaml="""
application:
  input:
    mascot_dat:
    - bfabric@fgcz-s-018.uzh.ch//usr/local/mascot/:/data/20150807/F221967.dat
    - bfabric@fgcz-s-018.uzh.ch//usr/local/mascot/:/data/20150807/F221973.dat
  output:
  - bfabric@fgczdata.fgcz-net.unizh.ch:/srv/www/htdocs//p1000/bfabric/Proteomics/gerneric_yaml/2015/2015-09/2015-09-02//workunit_134904//203196.zip
  parameters:
    gelcms: 'true'
    mudpit: 'false'
    qmodel: None
    xtandem: 'false'
  protocol: scp
job_configuration:
  executable: /usr/local/fgcz/proteomics/bin/fgcz_scaffold.bash
  external_job_id: 45915
  input:
    mascot_dat:
    - 201919
    - 201918
  output:
    protocol: scp
    resource_id: 203198
    ssh_args: -o StrictHostKeyChecking=no -c arcfour -2 -l bfabric -x
  stderr:
    protocol: file
    resource_id: 203197
    url: /home/bfabric/sgeworker/logs/workunitid-134904_resourceid-203196.err
  stdout:
    protocol: file
    resource_id: 203198
    url: /home/bfabric/sgeworker/logs/workunitid-134904_resourceid-203196.out
  workunit_id: 134904
"""

    job_config = yaml.load(example_yaml)
    if job_config['job_configuration']['executable']:
        print job_config['job_configuration']['executable']

    if job_config['application']['output']:
        print ",".join(job_config['application']['output'])

    bfapp = BfabricSubmitter(login='pfeeder',
                                 externaljobid=1,
                                 queue=None)


    print bfapp.compose_bash_script(example_yaml)
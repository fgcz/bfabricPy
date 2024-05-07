import base64
import datetime
import json
import os

import yaml

from bfabric.bfabric_legacy import bfabricEncoder
from bfabric.wrapper_creator.bfabric_external_job import BfabricExternalJob


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
                                        'resource_url': "{0}/userlab/show-resource.html?id={1}".format(self.config.base_url, resource_iterator._id)}


                if not sample_id is None:
                    _resource_sample['sample_id'] = int(sample_id)
                    _resource_sample['sample_url'] = "{0}/userlab/show-sample.html?id={1}".format(self.config.base_url, sample_id)

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
                'workunit_createdby': str(workunit.createdby),
                'workunit_url': "{0}/userlab/show-workunit.html?workunitId={1}".format(self.config.base_url, workunit._id),
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

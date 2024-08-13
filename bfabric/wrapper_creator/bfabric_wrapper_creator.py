from __future__ import annotations

import base64
import datetime
import json
from collections import defaultdict
from functools import cached_property
from pathlib import Path
from typing import Any, Literal

import yaml

from bfabric import Bfabric
from bfabric.bfabric_legacy import bfabricEncoder
from bfabric.entities import Workunit, ExternalJob, Application, Resource, Storage, Order, Project
from bfabric.experimental.app_interface.workunit_definition import WorkunitDefinition
from bfabric.wrapper_creator.bfabric_external_job import BfabricExternalJob


class BfabricWrapperCreator:
    def __init__(self, client: Bfabric, external_job_id: int) -> None:
        self._client = client
        self._external_job_id = external_job_id

    @cached_property
    def workunit_definition(self) -> WorkunitDefinition:
        return WorkunitDefinition.from_external_job_id(client=self._client, external_job_id=self._external_job_id)

    @cached_property
    def _external_job(self) -> ExternalJob:
        return ExternalJob.find(id=self._external_job_id, client=self._client)

    @cached_property
    def _workunit(self) -> Workunit:
        return self._external_job.workunit

    @cached_property
    def _application(self) -> Application:
        return self._workunit.application

    @cached_property
    def _log_storage(self) -> Storage:
        # this is SlurmLog
        return Storage.find(id=13, client=self._client)

    def create_output_resource(self) -> Resource:
        # Since we use the id of the output resource in the path, we have to save it twice.
        n_input_resource = len(self._workunit.input_resources)
        resource_id = self._client.save(
            "resource",
            {
                "name": f"{self._application.data_dict['name']} {n_input_resource} - resource",
                "workunitid": self._workunit.id,
                "storageid": self._application.storage.id,
                "relativepath": "/dev/null",
            },
        )[0]["id"]

        # Determine the correct path
        today = datetime.date.today()
        output_folder = Path(
            f"p{self._workunit.data_dict['container']['id']}",
            "bfabric",
            self._application.data_dict["technology"].replace(" ", "_"),
            self._application.data_dict["name"].replace(" ", "_"),
            today.strftime("%Y/%Y-%m/%Y-%m-%d/"),
            f"workunit_{self._workunit.id}",
        )
        output_filename = f"{resource_id}.{self._application.data_dict['outputfileformat']}"
        relative_path = str(output_folder / output_filename)

        # Save the path
        result = self._client.save("resource", {"id": resource_id, "relativepath": relative_path})
        return Resource(result[0])

    def create_log_resource(self, variant: Literal["out", "err"], output_resource: Resource) -> Resource:
        result = self._client.save(
            "resource",
            {
                "name": f"slurm_std{variant}",
                "workunitid": self.workunit_definition.workunit_id,
                "storageid": self._log_storage.id,
                "relativepath": f"/workunitid-{self._workunit.id}_resourceid-{output_resource.id}.{variant}",
            },
        )
        return Resource(result[0])

    def get_application_section(self, output_resource: Resource) -> dict[str, Any]:
        output_url = f"bfabric@{self._application.storage.data_dict['host']}:{self._application.storage.data_dict['basepath']}{output_resource.data_dict['relativepath']}"
        inputs = defaultdict(list)
        for resource in self.workunit_definition.execution.input_resources:
            inputs[resource.app_name].append(f"bfabric@{resource.scp_address}")
        return {
            "parameters": self.workunit_definition.parameter_values,
            "protocol": "scp",
            "input": dict(inputs),
            "output": [output_url],
        }

    def get_job_configuration_section(
        self, output_resource: Resource, stdout_resource: Resource, stderr_resource: Resource
    ) -> dict[str, Any]:
        log_resource = {}

        for name, resource in [("stdout", stdout_resource), ("stderr", stderr_resource)]:
            log_resource[name] = {
                "protocol": "file",
                "resource_id": resource.id,
                "url": str(Path(self._log_storage.data_dict["basepath"], resource.data_dict["relativepath"])),
            }

        inputs = defaultdict(list)
        for resource in self.workunit_definition.execution.input_resources:
            web_url = Resource({"id": resource.id}, client=self._client).web_url
            inputs[resource.app_name].append({"resource_id": resource.id, "resource_url": web_url})

        return {
            "executable": str(self.workunit_definition.executable_path),
            "external_job_id": self._external_job_id,
            "fastasequence": self._fasta_sequence,
            "input": dict(inputs),
            "inputdataset": None,
            "order_id": self.workunit_definition.order_id,
            "project_id": self.workunit_definition.project_id,
            "output": {
                "protocol": "scp",
                "resource_id": output_resource.id,
                "ssh_args": "-o StrictHostKeyChecking=no -2 -l bfabric -x",
            },
            "stderr": log_resource["stderr"],
            "stdout": log_resource["stdout"],
            "workunit_createdby": self._workunit.data_dict["createdby"],
            "workunit_id": self.workunit_definition.workunit_id,
            "workunit_url": self._workunit.web_url,
        }

    @cached_property
    def _order(self) -> Order | None:
        return self._workunit.container if isinstance(self._workunit.container, Order) else None

    @cached_property
    def _project(self) -> Project | None:
        return self._workunit.container if isinstance(self._workunit.container, Project) else self._order.project

    @cached_property
    def _fasta_sequence(self) -> str:
        if self._order is not None and "fastasequence" in self._order.data_dict:
            return "\n".join([x.strip() for x in str(self._order.data_dict["fastasequence"]).split("\r")])
        else:
            return ""

    def write_results(self, config_serialized: str) -> None:
        yaml_workunit_executable = self._client.save(
            "executable",
            {
                "name": "job configuration (executable) in YAML",
                "context": "WORKUNIT",
                "workunitid": self.workunit_definition.workunit_id,
                "description": "This is a job configuration as YAML base64 encoded. It is configured to be executed by the B-Fabric yaml submitter.",
                "base64": base64.b64encode(config_serialized.encode()).decode(),
                "version": "10",
            },
        )[0]
        yaml_workunit_externaljob = self._client.save(
            "externaljob",
            {
                "workunitid": self.workunit_definition.workunit_id,
                "status": "new",
                "executableid": yaml_workunit_executable["id"],
                "action": "WORKUNIT",
            },
        )

        # TODO now i am a bit confused, the external_job_id that is added to the .yml file is not the original one
        #      but rather the one from the yaml_workunit_externaljob. I am not sure if we need this as it makes the
        #      code here a lot more complex

        print(yaml_workunit_externaljob)
        self._client.save("externaljob", {"id": self._external_job_id, "status": "done"})


class BfabricWrapperCreatorOld(BfabricExternalJob):
    """
    the class is used for the wrapper_creator which is executed by the bfabtic system
    (non batch) so each resource is processed seperate
    """

    (externaljobid_submitter, workunit_executableid) = (None, None)

    def get_externaljobid_yaml_workunit(self):
        return self.externaljobid_yaml_workunit

    def get_executableid(self):
        return self.workunit_executableid

    def write_yaml(self, data_serializer=lambda x: yaml.dump(x, default_flow_style=False, encoding=None)):
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

        workunit = self.read_object(endpoint="workunit", obj={"id": workunitid})[0]
        if workunit is None:
            raise ValueError("ERROR: no workunit available for the given externaljobid.")

        assert isinstance(workunit._id, int)

        application = self.read_object("application", obj={"id": workunit.application._id})[0]
        # TODO(cp): rename to application_execuatbel
        workunit_executable = self.read_object("executable", obj={"id": workunit.applicationexecutable._id})[0]
        try:
            self.workunit_executableid = workunit_executable._id
        except:
            self.workunit_executableid = None

        # Get container details
        container = workunit.container
        fastasequence = ""
        if container._classname == "order":
            order = self.read_object("order", obj={"id": container._id})[0]
            order_id = order._id
            if "project" in order:  # noqa
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
        _output_storage = self.read_object("storage", obj={"id": application.storage._id})[0]

        _output_relative_path = "p{0}/bfabric/{1}/{2}/{3}/workunit_{4}/".format(  # noqa
            container._id,
            application.technology.replace(" ", "_"),
            application.name.replace(" ", "_"),
            today.strftime("%Y/%Y-%m/%Y-%m-%d/"),
            workunitid,
        )

        # Setup the log_storage to SlurmLog with id 13
        _log_storage = self.read_object("storage", obj={"id": 13})[0]

        # _cmd_applicationList = [workunit_executable.program]

        application_parameter = {}

        if getattr(workunit, "parameter", None) is not None:
            for para in workunit.parameter:
                parameter = self.read_object("parameter", obj={"id": para._id})
                if parameter:
                    for p in parameter:
                        try:
                            application_parameter[f"{p.key}"] = f"{p.value}"
                        except:
                            application_parameter[f"{p.key}"] = ""

        try:
            input_resources = [x._id for x in workunit.inputresource]
            input_resources = [self.read_object(endpoint="resource", obj={"id": x})[0] for x in input_resources]
        except:
            print("no input resources found. continue with empty list.")
            input_resources = []

        # query all urls and ids of the input resources
        resource_urls = dict()
        resource_ids = dict()

        for resource_iterator in input_resources:
            try:
                _appication_id = self.read_object(endpoint="workunit", obj={"id": resource_iterator.workunit._id})[
                    0
                ].application._id

                _application_name = f"{self.read_object('application', obj={'id': _appication_id})[0].name}"

                _storage = self.read_object("storage", {"id": resource_iterator.storage._id})[0]

                _inputUrl = f"bfabric@{_storage.host}:/{_storage.basepath}/{resource_iterator.relativepath}"

                if _application_name not in resource_urls:
                    resource_urls[_application_name] = []
                    resource_ids[_application_name] = []

                resource_urls[_application_name].append(_inputUrl)

                sample_id = self.get_sampleid(int(resource_iterator._id))

                _resource_sample = {
                    "resource_id": int(resource_iterator._id),
                    "resource_url": f"{self.config.base_url}/userlab/show-resource.html?id={resource_iterator._id}",
                }

                if sample_id is not None:
                    _resource_sample["sample_id"] = int(sample_id)
                    _resource_sample["sample_url"] = f"{self.config.base_url}/userlab/show-sample.html?id={sample_id}"

                resource_ids[_application_name].append(_resource_sample)
            except:
                print("resource_iterator failed. continue ...")
                pass

        # create resources for output, stderr, stdout
        _ressource_output = self.save_object(
            "resource",
            {
                "name": f"{application.name} {len(input_resources)} - resource",
                "workunitid": workunit._id,
                "storageid": int(application.storage._id),
                "relativepath": _output_relative_path,
            },
        )[0]

        print(_ressource_output)
        _output_filename = f"{_ressource_output._id}.{application.outputfileformat}"
        # we want to include the resource._id into the filename
        _ressource_output = self.save_object(
            "resource",
            {
                "id": int(_ressource_output._id),
                "relativepath": f"{_output_relative_path}/{_output_filename}",
            },
        )[0]

        print(_ressource_output)
        _resource_stderr = self.save_object(
            "resource",
            {
                "name": "slurm_stderr",
                "workunitid": int(workunit._id),
                "storageid": _log_storage._id,
                "relativepath": f"/workunitid-{workunit._id}_resourceid-{_ressource_output._id}.err",
            },
        )[0]

        _resource_stdout = self.save_object(
            "resource",
            {
                "name": "slurm_stdout",
                "workunitid": workunit._id,
                "storageid": _log_storage._id,
                "relativepath": f"/workunitid-{workunit._id}_resourceid-{_ressource_output._id}.out",
            },
        )[0]

        # Creates the workunit executable
        # The config includes the externaljobid: the yaml_workunit_externaljob has to be created before it.
        # The yaml_workunit_externaljob cannot be created without specifying an executableid:
        # a yaml_workunit_executable is thus created before the config definition in order to provide
        # the correct executableid to the yaml_workunit_externaljob.
        # However this yaml_workunit_executable has to be updated later to include 'base64': base64.b64encode(config_serialized.encode()).decode()
        yaml_workunit_executable = self.save_object(
            "executable",
            {
                "name": "job configuration (executable) in YAML",
                "context": "WORKUNIT",
                "workunitid": workunit._id,
                "description": "This is a job configuration as YAML base64 encoded. It is configured to be executed by the B-Fabric yaml submitter.",
            },
        )[0]
        print(yaml_workunit_executable)

        yaml_workunit_externaljob = self.save_object(
            "externaljob",
            {
                "workunitid": workunit._id,
                "status": "new",
                "executableid": yaml_workunit_executable._id,
                "action": "WORKUNIT",
            },
        )[0]
        print(yaml_workunit_externaljob)
        assert isinstance(yaml_workunit_externaljob._id, int)
        self.externaljobid_yaml_workunit = int(yaml_workunit_externaljob._id)
        print(f"XXXXXXX self.externaljobid_yaml_workunit ={self.externaljobid_yaml_workunit} XXXXXXX")

        _output_url = (
            f"bfabric@{_output_storage.host}:{_output_storage.basepath}{_output_relative_path}/{_output_filename}"
        )

        try:
            query_obj = {"id": workunit.inputdataset._id}
            inputdataset = self.read_object(endpoint="dataset", obj=query_obj)[0]
            inputdataset_json = json.dumps(inputdataset, cls=bfabricEncoder, sort_keys=True, indent=2)
            inputdataset = json.loads(inputdataset_json)
        except:
            inputdataset = None

        # Compose configuration structure
        config = {
            "job_configuration": {
                "executable": f"{workunit_executable.program}",
                "inputdataset": inputdataset,
                "input": resource_ids,
                "output": {
                    "protocol": "scp",
                    "resource_id": int(_ressource_output._id),
                    "ssh_args": "-o StrictHostKeyChecking=no -2 -l bfabric -x",
                },
                "stderr": {
                    "protocol": "file",
                    "resource_id": int(_resource_stderr._id),
                    "url": f"{_log_storage.basepath}/workunitid-{workunit._id}_resourceid-{_ressource_output._id}.err",
                },
                "stdout": {
                    "protocol": "file",
                    "resource_id": int(_resource_stdout._id),
                    "url": f"{_log_storage.basepath}/workunitid-{workunit._id}_resourceid-{_ressource_output._id}.out",
                },
                "workunit_id": int(workunit._id),
                "workunit_createdby": str(workunit.createdby),
                "workunit_url": f"{self.config.base_url}/userlab/show-workunit.html?workunitId={workunit._id}",
                "external_job_id": int(yaml_workunit_externaljob._id),
                "order_id": order_id,
                "project_id": project_id,
                "fastasequence": fastasequence,
            },
            "application": {
                "protocol": "scp",
                "parameters": application_parameter,
                "input": resource_urls,
                "output": [_output_url],
            },
        }

        config_serialized = data_serializer(config)
        print(config_serialized)

        yaml_workunit_executable = self.save_object(
            "executable",
            {
                "id": yaml_workunit_executable._id,
                "base64": base64.b64encode(config_serialized.encode()).decode(),
                "version": f"{10}",
            },
        )[0]
        print(yaml_workunit_executable)

        # The WrapperCreator executable is successful, and the status of the its external job is set to done,
        # which triggers B-Fabric to create an external job for the submitter executable.

        wrapper_creator_externaljob = self.save_object(
            endpoint="externaljob", obj={"id": self.externaljobid, "status": "done"}
        )

        print(f"\n\nquery_counter={self.query_counter}")

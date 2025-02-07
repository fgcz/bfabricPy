from __future__ import annotations

import base64
from collections import defaultdict
from functools import cached_property
from pathlib import Path
from typing import Any, Literal

import yaml
from loguru import logger

from bfabric import Bfabric
from bfabric.entities import (
    Workunit,
    ExternalJob,
    Application,
    Resource,
    Storage,
    Order,
    Project,
)
from bfabric.experimental.workunit_definition import WorkunitDefinition


class BfabricWrapperCreator:
    def __init__(self, client: Bfabric, external_job_id: int) -> None:
        self._client = client
        self._external_job_id = external_job_id

    @cached_property
    def workunit_definition(self) -> WorkunitDefinition:
        return WorkunitDefinition.from_workunit(self._external_job.workunit)

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
        logger.info("Creating output resource")
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
        output_folder = self._workunit.store_output_folder
        output_filename = f"{resource_id}.{self._application.data_dict['outputfileformat']}"
        relative_path = str(output_folder / output_filename)

        # Save the path
        logger.info("Saving correct path")
        result = self._client.save("resource", {"id": resource_id, "relativepath": relative_path})
        return Resource(result[0])

    def create_log_resource(self, variant: Literal["out", "err"], output_resource: Resource) -> Resource:
        logger.info("Creating log resource")
        result = self._client.save(
            "resource",
            {
                "name": f"slurm_std{variant}",
                "workunitid": self.workunit_definition.registration.workunit_id,
                "storageid": self._log_storage.id,
                "relativepath": f"workunitid-{self._workunit.id}_resourceid-{output_resource.id}.{variant}",
            },
        )
        return Resource(result[0])

    def get_application_section(self, output_resource: Resource) -> dict[str, Any]:
        logger.info("Creating application section")
        output_url = f"bfabric@{self._application.storage.data_dict['host']}:{self._application.storage.data_dict['basepath']}{output_resource.data_dict['relativepath']}"
        inputs = defaultdict(list)
        for resource in Resource.find_all(self.workunit_definition.execution.resources, client=self._client).values():
            inputs[resource.workunit.application["name"]].append(
                f"bfabric@{resource.storage.scp_prefix}{resource.data_dict['relativepath']}"
            )
        return {
            "parameters": self.workunit_definition.execution.raw_parameters,
            "protocol": "scp",
            "input": dict(inputs),
            "output": [output_url],
        }

    def get_job_configuration_section(
        self,
        output_resource: Resource,
        stdout_resource: Resource,
        stderr_resource: Resource,
    ) -> dict[str, Any]:
        logger.info("Creating job configuration section")
        log_resource = {}

        for name, resource in [
            ("stdout", stdout_resource),
            ("stderr", stderr_resource),
        ]:
            log_resource[name] = {
                "protocol": "file",
                "resource_id": resource.id,
                "url": str(
                    Path(
                        self._log_storage.data_dict["basepath"],
                        resource.data_dict["relativepath"],
                    )
                ),
            }

        inputs = defaultdict(list)
        for resource in Resource.find_all(self.workunit_definition.execution.resources, client=self._client).values():
            web_url = Resource({"id": resource.id}, client=self._client).web_url
            inputs[resource.workunit.application["name"]].append({"resource_id": resource.id, "resource_url": web_url})

        return {
            "executable": str(self._workunit.application.executable["program"]),
            "external_job_id": self._external_job_id,
            "fastasequence": self._fasta_sequence,
            "input": dict(inputs),
            "inputdataset": None,
            "order_id": self._order.id if self._order is not None else None,
            "project_id": self._project.id,
            "output": {
                "protocol": "scp",
                "resource_id": output_resource.id,
                "ssh_args": "-o StrictHostKeyChecking=no -2 -l bfabric -x",
            },
            "stderr": log_resource["stderr"],
            "stdout": log_resource["stdout"],
            "workunit_createdby": self._workunit.data_dict["createdby"],
            "workunit_id": self.workunit_definition.registration.workunit_id,
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

    def write_results(self, config_serialized: str) -> tuple[dict[str, Any], dict[str, Any]]:
        logger.info("Saving executable")
        yaml_workunit_executable = self._client.save(
            "executable",
            {
                "name": "job configuration (executable) in YAML",
                "context": "WORKUNIT",
                "workunitid": self.workunit_definition.registration.workunit_id,
                "description": "This is a job configuration as YAML base64 encoded. It is configured to be executed by the B-Fabric yaml submitter.",
                "base64": base64.b64encode(config_serialized.encode()).decode(),
                "version": "10",
            },
        )[0]
        logger.info("Saving external job")
        yaml_workunit_externaljob = self._client.save(
            "externaljob",
            {
                "workunitid": self.workunit_definition.registration.workunit_id,
                "status": "new",
                "executableid": yaml_workunit_executable["id"],
                "action": "WORKUNIT",
            },
        )[0]

        # TODO now i am a bit confused, the external_job_id that is added to the .yml file is not the original one
        #      but rather the one from the yaml_workunit_externaljob. I am not sure if we need this as it makes the
        #      code here a lot more complex

        logger.info(yaml_workunit_externaljob)
        logger.info("Setting external job status to 'done'")
        self._client.save("externaljob", {"id": self._external_job_id, "status": "done"})

        return yaml_workunit_executable, yaml_workunit_externaljob

    def create(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Creates the YAML file external job and resources, and registers everything in B-Fabric."""
        output_resource = self.create_output_resource()
        stdout_resource = self.create_log_resource(variant="out", output_resource=output_resource)
        stderr_resource = self.create_log_resource(variant="err", output_resource=output_resource)

        config_dict = {
            "application": self.get_application_section(output_resource=output_resource),
            "job_configuration": self.get_job_configuration_section(
                output_resource=output_resource,
                stdout_resource=stdout_resource,
                stderr_resource=stderr_resource,
            ),
        }
        config_serialized = yaml.safe_dump(config_dict)
        yaml_workunit_executable, yaml_workunit_externaljob = self.write_results(config_serialized=config_serialized)
        return config_dict, yaml_workunit_executable, yaml_workunit_externaljob

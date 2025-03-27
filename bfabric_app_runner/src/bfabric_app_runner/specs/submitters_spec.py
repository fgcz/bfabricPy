from __future__ import annotations

from pathlib import Path
from typing import Literal, Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, AliasChoices, model_validator

from bfabric_app_runner.specs.config_interpolation import Variables, interpolate_config_strings


class SubmitterSlurmConfigSpec(BaseModel):
    slurm_root: Path = Field(validation_alias=AliasChoices("slurm_root", "slurm-root"))
    local_script_dir: Path = Field(validation_alias=AliasChoices("local_script_dir", "local-script-dir"))
    worker_scratch_dir: Path = Field(validation_alias=AliasChoices("worker_scratch_dir", "worker-scratch-dir"))
    log_storage_id: int | None = Field(validation_alias=AliasChoices("log_storage_id", "log-storage-id"), default=None)
    log_storage_resource_name: str | None = Field(
        validation_alias=AliasChoices("log_storage_resource_name", "log-storage-resource-name"), default=None
    )
    log_storage_filename: str | None = Field(
        validation_alias=AliasChoices("log_storage_filename", "log-storage-filename"), default=None
    )
    force_storage: Path | None = Field(validation_alias=AliasChoices("force_storage", "force-storage"), default=None)

    @model_validator(mode="after")
    def either_full_or_no_log_config(self) -> SubmitterSlurmConfigSpec:
        if self.log_storage_id is None and self.log_storage_filename is None and self.log_storage_resource_name is None:
            return self
        if (
            self.log_storage_id is not None
            and self.log_storage_resource_name is not None
            and self.log_storage_filename is not None
        ):
            return self
        raise ValueError("Either all log storage parameters must be provided, or none of them")


class SubmitterSlurmSpec(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    type: Literal["slurm"]
    params: dict[Annotated[str, StringConstraints(pattern="^--.*")], str | None]
    config: SubmitterSlurmConfigSpec


class SubmittersSpec(BaseModel):
    submitters: dict[str, SubmitterSlurmSpec]


class SubmittersSpecTemplate(BaseModel):
    submitters: dict[str, SubmitterSlurmSpec]

    def evaluate(self, variables: Variables) -> SubmittersSpec:
        """Evaluates the template to a concrete ``SubmittersSpec`` instance."""
        template_data = self.model_dump(mode="json")
        data = interpolate_config_strings(data=template_data, variables=variables)
        return SubmittersSpec.model_validate(data)

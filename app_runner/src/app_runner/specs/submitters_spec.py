from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, constr

from app_runner.specs.config_interpolation import Variables, interpolate_config_strings


class SubmitterSlurmConfigSpec(BaseModel):
    slurm_root: Path = Field(alias="slurm-root")
    local_script_dir: Path = Field(alias="local-script-dir")
    worker_scratch_dir: Path = Field(alias="worker-scratch-dir")


class SubmitterSlurmSpec(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    type: Literal["slurm"]
    params: dict[constr(pattern="^--.*"), str | None]
    config: SubmitterSlurmConfigSpec


class SubmittersSpecTemplate(BaseModel):
    submitters: dict[str, SubmitterSlurmSpec]

    def evaluate(self, variables: Variables) -> SubmittersSpec:
        data_template = self.model_dump(mode="json")
        data = interpolate_config_strings(data_template, variables=variables.model_dump(mode="python"))
        return SubmittersSpec.model_validate(data)


class SubmittersSpec(BaseModel):
    submitters: dict[str, SubmitterSlurmSpec]

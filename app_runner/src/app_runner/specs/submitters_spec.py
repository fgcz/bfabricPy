from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app_runner.specs.config_interpolation import Variables, interpolate_config_strings

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal


class SubmitterSlurmConfig(BaseModel):
    local_script_dir: Path = Field(alias="local-script-dir")
    worker_scratch_dir: Path = Field(alias="worker-scratch-dir")


class SubmitterSlurm(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    type: Literal["slurm"]
    params: dict[str, str | None]
    config: SubmitterSlurmConfig


class SubmittersSpecTemplate(BaseModel):
    submitters: dict[str, SubmitterSlurm]

    def evaluate(self, variables: Variables) -> SubmittersSpec:
        data_template = self.model_dump(mode="json")
        data = interpolate_config_strings(data_template, variables=variables.model_dump(mode="python"))
        return SubmittersSpec.model_validate(data)


class SubmittersSpec(BaseModel):
    submitters: dict[str, SubmitterSlurm]

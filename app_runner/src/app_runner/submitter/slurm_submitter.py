from __future__ import annotations

import os
import subprocess
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel


if TYPE_CHECKING:
    from app_runner.specs.submitters_spec import SubmitterSlurmSpec
    from bfabric.entities import ExternalJob


class SlurmSubmitterSpecialStrings(Enum):
    default = "[default]"
    auto = "[auto]"

    @classmethod
    def parse(cls, string: str) -> SlurmSubmitterSpecialStrings | None:
        if string == cls.default.value:
            return cls.default
        elif string == cls.auto.value:
            return cls.auto
        else:
            return None


class SlurmSubmitterUserParams(BaseModel):
    partition: str
    nodeslist: str
    memory: str


_MAIN_BASH_TEMPLATE = """
tee app_version.yml <<YAML
{app_version_yml}
YAML

tee workunit_definition.yml <<'YAML'
{workunit_definition_yml}
YAML

bfabric-app-runner app run --app-version app_version.yml --workunit-ref workunit_definition.yml --work-dir "$(pwd)"
"""


class SlurmSubmitter:
    def __init__(self, default_config: SubmitterSlurmSpec) -> None:
        self._default_config = default_config

    def _get_concrete_params(self, specific_params: dict[str, str | None]) -> dict[str, str]:
        merged = {**self._default_config.params, **specific_params}
        return {key: value for key, value in merged.items() if value is not None}

    def _compose_script_header(self, concrete_params: dict[str, str]) -> str:
        return "\n".join(["#!/bin/bash"] + [f"#SBATCH {key}={value}" for key, value in concrete_params.items()])

    def _compose_script(self, main_command: str, specific_params: dict[str, str | None]) -> str:
        concrete_params = self._get_concrete_params(specific_params)
        script_header = self._compose_script_header(concrete_params)
        return f"{script_header}\n\n{main_command}"

    def _interpolate_main(self, app_version_yml: str, workunit_definition_yml: str) -> str:
        return _MAIN_BASH_TEMPLATE.format(
            app_version_yml=app_version_yml, workunit_definition_yml=workunit_definition_yml
        )

    def submit(self, external_job: ExternalJob, specific_params: dict[str, str | None]) -> None:
        # Determine the script path
        executable = external_job.executable
        workunit_id = external_job.workunit.id
        script_path = (
            self._default_config.config.local_script_dir
            / f"workunitid-{workunit_id}_externaljobid-{external_job.id}_executableid-{executable.id}.bash"
        )

        # TODO missing args
        main_command = self._interpolate_main()

        # Generate the script
        script = self._compose_script(main_command=main_command, specific_params=specific_params)
        script_path.write_text(script)

        # Execute sbatch
        sbatch_bin = self._default_config.config.slurm_root / "bin" / "sbatch"
        env = os.environ | {"SLURMROOT": self._default_config.config.slurm_root}
        # TODO remove after debug
        print(script_path)
        # TODO remove after debug
        1 / 0
        subprocess.run([str(sbatch_bin), str(script_path)], env=env, check=True)

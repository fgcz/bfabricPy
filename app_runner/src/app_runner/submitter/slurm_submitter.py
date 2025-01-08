from typing import TextIO

from app_runner.specs.submitter_spec import SubmitterSlurmSpec


class SubmitterSlurm:
    def __init__(self, spec: SubmitterSlurmSpec) -> None:
        self._spec = spec

    def submit(self) -> None:
        # TODO this should receive basically the main command, create the slurm script and then submit it...
        #      -> specific configuration is needed
        pass

    def compose_script(self, out: TextIO) -> None:
        print("#!/bin/bash", file=out)
        for arg in self._spec.to_slurm_args():
            print(f"#SBATCH {arg}", file=out)

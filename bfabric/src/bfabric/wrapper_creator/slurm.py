from __future__ import annotations

from loguru import logger

"""
Interface to the SLURM (Simple Linux Utility for Resources Management) resource manager and job scheduler

2020-09-28
Maria d'Errico
Christian Panse
"""

# Copyright (C) 2011, 2012 ETH Zurich and University of Zurich. All rights reserved.
# Copyright (C) 2014 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Christian Panse <cp@fgcz.ethz.ch>
#   Maria d'Errico <maria.derrico@fgcz.ethz.ch>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from pathlib import Path
import os
import subprocess


class SLURM:
    """Wrapper for SLURM, providing a Python interface to `sbatch`.

    The `slurm_root` variable will be passed as `SLURMROOT` to the environment, when submitting the script, and is an
    important parameter which needs to be set correctly for our scripts to function properly.
    """

    def __init__(self, slurm_root: str | Path = "/usr/") -> None:
        self._slurm_root = Path(slurm_root)
        self._sbatch_bin = self._slurm_root / "bin/sbatch"

    def sbatch(self, script: str | Path) -> tuple[str, str] | None:
        """Submits the script to SLURM using `sbatch`.
        If successful, returns a tuple with the stdout and stderr of the submission.
        """
        script = Path(script)
        if not script.is_file():
            logger.error(f"Script not found: {script}")
            return
        if not self._sbatch_bin.is_file():
            logger.error(f"sbatch binary not found: {self._sbatch_bin}")
            return

        env = os.environ | {"SLURMROOT": self._slurm_root}
        result = subprocess.run(
            [str(self._sbatch_bin), str(script)],
            env=env,
            check=True,
            shell=False,
            capture_output=True,
            encoding="utf-8",
        )
        # TODO the code initially had a TODO to write these two to a file, in general I think the logs of the squeue
        #      are currently not written to a file at all.
        return result.stdout, result.stderr

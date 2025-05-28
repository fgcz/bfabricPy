#!/bin/bash
% for key, value in sbatch_params.items():
#SBATCH ${key}=${value}
% endfor
set -euxo pipefail
{
${wrapped_script}
} 2>&1 | awk '{print strftime("[%Y-%m-%d %H:%M:%S]"), $0; fflush()}'

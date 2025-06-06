#!/bin/bash
% for key, value in sbatch_params.items():
#SBATCH ${key}=${value}
% endfor
set -euo pipefail
{
set -x
id
hostname
export PYTHONUNBUFFERED=1
export BFABRICPY_CONFIG_ENV=$BFABRICPY_CONFIG_ENV
${wrapped_script}
} 2>&1 | while read line; do echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"; done

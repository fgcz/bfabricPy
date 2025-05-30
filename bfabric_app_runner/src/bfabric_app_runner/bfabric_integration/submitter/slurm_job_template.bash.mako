#!/bin/bash
% for key, value in sbatch_params.items():
#SBATCH ${key}=${value}
% endfor
set -euo pipefail
set +x
cleanup_on_exit() {
    local code=$?
    if [ $code -ne 0 ]; then
        ${python_interpreter} -m bfabric_app_runner.bfabric_integration.api report-workunit-failed ${workunit_id}
    fi
    exit $code
}
trap cleanup_on_exit EXIT
{
set -x
id
hostname
export PYTHONUNBUFFERED=1
${wrapped_script}
} 2>&1 | while read line; do echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"; done
${python_interpreter} -m bfabric_app_runner.bfabric_integration.api report-workunit-done ${workunit_id}

#!/bin/bash
% for key, value in sbatch_params.items():
#SBATCH ${key}=${value}
% endfor
set -euxo pipefail
hostname
id
mkdir -p "${working_directory}"
cd "${working_directory}"

set +x
tee app_version.yml <<YAML
${app_version_yml}
YAML

tee workunit_definition.yml <<YAML
${workunit_definition_yml}
YAML
trap 'code=$?; [ $code -ne 0 ] && bfabric-cli api update workunit ${workunit_id} status failed --no-confirm; exit $code' EXIT

set -x
bfabric-cli api update workunit ${workunit_id} status processing --no-confirm
% if logging_resource_id is not None:
bfabric-cli api update resource ${logging_resource_id} status available --no-confirm
% endif

export PYTHONUNBUFFERED=1
{
${command}
} 2>&1 | ts '[%Y-%m-%d %H:%M:%S]'

exit 0

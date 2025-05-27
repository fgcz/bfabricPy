# shellcheck disable=SC2016
# Setup
set -euxo pipefail
hostname
id
export PYTHONUNBUFFERED=1

# Set the workunit status to failed, if the script exits with a non-zero error code.
trap 'code=$?; [ $code -ne 0 ] && bfabric-cli api update workunit ${workunit_id} status failed --no-confirm; exit $code' EXIT

# Determine the binaries to use - we use uv for this
bfabric_cli_bin=uv run --with '${dependencies.bfabric_scripts}' bfabric-cli
bfabric_app_runner_bin=uv run --with '${dependencies.bfabric_app_runner}' bfabric-app-runner

# Create the scratch directory.
mkdir -p '${working_directory}'
cd '${working_directory}'

$bfabric_cli_bin api update workunit '${workunit_id}' status processing --no-confirm
$bfabric_app_runner_bin prepare workunit '${app_yaml_path}' --work-dir '${working_directory}' --workunit-ref '${workunit_id}'
make run-all

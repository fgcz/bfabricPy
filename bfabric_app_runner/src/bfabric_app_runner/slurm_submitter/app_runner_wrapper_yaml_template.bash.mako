# shellcheck disable=SC2016
# Setup
set -euxo pipefail
hostname
id
export PYTHONUNBUFFERED=1

# Determine the binaries to use - we use uv for this
bfabric_cli_bin="uv run --with ${dependencies["bfabric_scripts"]} bfabric-cli"
bfabric_app_runner_bin="uv run --with ${dependencies["bfabric_app_runner"]} bfabric-app-runner"

# Set the workunit status to failed, if the script exits with a non-zero error code.
trap 'code=$?; [ $code -ne 0 ] && $bfabric_cli_bin api update workunit ${workunit_id} status failed --no-confirm; exit $code' EXIT

$bfabric_app_runner_bin run workunit --app-definition '${app_yaml_path}' --scratch-root /scratch --workunit-ref '${workunit_id}'

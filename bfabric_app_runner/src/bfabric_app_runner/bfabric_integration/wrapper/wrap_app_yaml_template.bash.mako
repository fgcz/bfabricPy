# shellcheck disable=SC2016,SC2154
# Determine the binaries to use - we use uv for this
bfabric_app_runner_bin="uv run --with ${dependencies["bfabric_app_runner"]} bfabric-app-runner"
$bfabric_app_runner_bin run workunit --app-definition '${app_yaml_path}' --scratch-root /scratch --workunit-ref '${workunit_id}'

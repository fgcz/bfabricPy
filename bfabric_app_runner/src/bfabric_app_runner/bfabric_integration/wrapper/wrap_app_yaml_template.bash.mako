# shellcheck disable=SC2016,SC2154
# Determine app runner version
app_runner_version=$("${python_interpreter}" -m bfabric_app_runner.bfabric_integration.api read-app-yaml-app-runner-dependency "${app_yaml_path}")

# Run
uv run --with "$app_runner_version" bfabric-app-runner \
    run workunit --app-definition '${app_yaml_path}' --scratch-root '${scratch_root}' --workunit-ref '${workunit_id}'

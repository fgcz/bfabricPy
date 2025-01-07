from app_runner.specs.app.app_spec import AppVersions, AppVersion
from bfabric.experimental.workunit_definition import WorkunitDefinition


def resolve_app(versions: AppVersions, workunit_definition: WorkunitDefinition) -> AppVersion:
    """Resolves the app version to use for the provided workunit definition."""
    # TODO this should be more generic in the future
    # TODO logic to define "latest" version
    app_version = workunit_definition.execution.raw_parameters["application_version"]
    # TODO graceful handling of invalid versions
    return versions[app_version]

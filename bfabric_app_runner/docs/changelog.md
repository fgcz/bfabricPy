# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## \[Unreleased\]

### Changed

- Automatic workflow step creation is moved from `dispatch` action to `stage` action, to avoid creating workflowsteps
    for failed workunits. We might revisit this decision in the future, as there could be some benefit to creating the
    workflowstep early on.

## \[0.3.1\] - 2025-09-01

### Added

- `CommandPythonEnv` can also execute any tools available in the Python environment (in `.venv/bin`), not just modules.
- `-m bfabric_app_runner.commands.command_python_env` provides an experimental CLI to run arbitrary commands analogously to the app runner.
- Automatically save links to workunits without specifying extra IDs.

# Changed

- Dispatch action detects, when the script modifies `workunit_definition.yml` which should not happen anymore, and notifies
    the user restoring the original file. The app continues without an error.

## \[0.3.0\] - 2025-08-26

### Added

- Add `workflow_template_step_id` field to `BfabricAppSpec` to specify template step to register workunits under automatically.
- Dispatch action checks if a workflow template step is specified and registers the workunit under it automatically.

### Changed

- Generic dispatch functionality will not override existing `workunit_definition.yml` files anymore.
- Update `bfabric` dependency to 1.13.33.

## \[0.2.1\] - 2025-07-22

### Fixed

- Makefile avoids redundant dispatch on every target.

## \[0.2.0\] - 2025-07-15

This release consolidates various commands in bfabric-app-runner streamlining the user experience.
It also brings an improved Makefile which should obsolete the manual installation of `bfabric-app-runner` providing
the user with the configured version by default.

### Removed

- Removed experimental `bfabric-app-runner deploy build-app-zip` command and associated app.zip functionality. This functionality has been superseded by the more robust `CommandPythonEnv` approach for Python environment management.
- Removed `bfabric-app-runner app` command (covered by `bfabric-app-runner run` and `bfabric-app-runner prepare` now).
- Removed `bfabric-app-runner chunk` command (covered by `bfabric-app-runner action` now).
- Removed module path support for app specification. `CommandPythonEnv` is cleaner than the workflow this tried to enable.
- The app related commands do not support `AppVersion` inputs anymore. Instead, you should always specify a `AppSpec` file.

### Changed

- `bfabric-app-runner prepare workunit` does not accept module refs anymore and will resolve the app spec path.
- `bfabric-app-runner prepare workunit --force-app-version` to force a specific app version for the workunit.
- Old `bfabric-app-runner app run` and `bfabric-app-runner app dispatch` use the new makefile function from cmd_prepare.

### Added

- `copier` based template/demo application for development and end-to-end testing of bfabric-app-runner.
- Added `ResolvedDirectory` type to represent directories resolved from resource archives.
- Added `BfabricResourceArchiveSpec` to specify input archives which should be extracted  (and select which files are needed).
- Validation logic has been added for `ResolvedDirectory` and `BfabricResourceArchiveSpec`. In particular a `ResolvedDirectory` may never overlap with a `ResolvedFile` or `ResolvedStaticFile` path.
- Using `uv tool` the Makefile will provide the correct version of the app runner when called. To opt-out of this behavior, one can set `USE_EXTERNAL_RUNNER=true` for the makefile.

## \[0.1.2\] - 2025-07-08

### Changed

- `CommandPythonEnv` with `refresh=True` now will create a separate environment to avoid breaking apps which are already using a particular
    Python environment without locking it.

## \[0.1.1\] - 2025-07-07

### Changed

- `CommandPythonEnv` computes the hash more carefully.

## \[0.1.0\] - 2025-06-27

### Added

- Command type `python_env` for commands which require a provisioned Python environment.

### Changed

- Command implementation is separated from command definition for cleaner implementation.
- New submitter requires `BFABRICPY_CONFIG_ENV` and `XDG_CACHE_HOME` to be set.
- Update `bfabric` dependency to 1.13.28.

## \[0.0.23\] - 2025-06-02

### Added

- `bfabric_app_runner.bfabric_integration.slurm` and associated packages.
- Command `bfabric-app-runner run workunit` to run the whole app end-to-end for a workunit.

### Removed

- AppVersion does not have a `submitter` field anymore.
- Some old submitter related functionality is deleted.

## \[0.0.22\] - 2025-05-21

### Added

- Apps can now be referred to by module path rather than just file paths. This is going to be a primary building block
    to very simple package-based deployment of apps.
- The `static_file` input spec type has been integrated properly.
- Missing integration for `file` input spec type has been added.
- The workunit makefile now directly shows how to use the GitHub app runner version instead, which is sometimes required
    while debugging.
- `CommandExec` allows prepending paths to `PATH` and setting environment variables and is less ambiguous than `shell`.
- `bfabric-app-runner action` interface which standardizes the various actions of running app steps.
- `bfabric-app-runner prepare workunit` to prepare a workunit execution and sets up a `app_env.yml` and `Makefile`.
- `bfabric-app-runner deploy build-app-zip` experimental command to build an app zip file which can be deployed, for a
    particular Python application.

### Changed

- Silently interpolate_config_strings log messages.
- Update `bfabric` dependency to 1.13.27.
- App versions do not always require a version key as it will default to "latest", but only one version can have a
    particular version key per app definition.

### Fixed

- Use most recent cyclopts version again, i.e. [issue 168](https://github.com/fgcz/bfabricPy/issues/168) is fixed.
- Compatibility with pandera 0.24.0 was restored.

## \[0.0.21\] - 2025-03-27

### Added

- `workunit` can now be interpolated in config files.
- `SubmittersSpec` to define a slurm submitter.

### Changed

- Submitter params in app definition, use key `params` rather than `config` to be more explicit.

### Fixed

- Temporary workaround for https://github.com/fgcz/bfabricPy/issues/168.

## \[0.0.20\] - 2025-03-25

### Changed

- Input staging is now more efficient for large numbers of similar input types,
    by batching the transformation into resolved operations.

### Fixed

- `workunit.mk` correctly chooses between `app_version.yml` and `app_definition.yml` depending on availability
- Multiple inputs with the same output filename, will yield an error now.
- File timestamps will not be modified anymore, if the file is already up-to-date.

### Added

- `SaveLinkSpec` to save a B-Fabric link e.g. to a workunit.

### Removed

- `file_scp` spec has been removed, one should use `file` instead (`FileSpec`)
- A lot of the old input handling code has been removed, it should not cause any problems, but mentioning this in case
    it shows up after the release.

## \[0.0.19\] - 2025-02-28

### Added

- `dispatch_resource_flow` output table allows null filename
- `--force-storage` is available in more commands now

### Changed

- The `workunit.mk` Makefile now specifies Python 3.13 in the uv venv, so it is more reliable.

## \[0.0.18\] - 2025-02-25

### Added

- `static_yaml` input type to write parameters etc.
- `dispatch.dispatch_resource_flow` implements a generic solution for dispatching resource flow workunits without
    having to perform entity look up in many cases yourself.
- App Definition now supports omitting the collect step.

### Changed

- `BfabricResourceSpec` defaults to file basename vs resource name, if no name is specified.

## \[0.0.17\] - 2025-02-19

### Fixed

- Update `bfabric` to 1.13.22 for dataset fix.

## \[0.0.16\] - 2025-02-19

### Added

- Implement `--force-storage` to pass a yaml to a forced storage instead of the real one.
- A Makefile will be created in the app folder for easier interaction with the app-runner (it uses uv and PyPI).

### Changed

- CopyResourceSpec.update_existing now defaults to `if_exists`.
- Resolve workunit_ref to absolute path if it is a Path instance for CLI.

## \[0.0.15\] - 2025-02-06

### Added

- New input type `file` which replaces `file_scp` and preserves timestamps whenever possible and allows to create
    symlinks instead of copying the file, as needed.
- `BfabricOrderFastaSpec.required` which allows specifying whether the order fasta is required or not

### Changed

- Better error when app version is not found.

### Fixed

- Config: Log messages are shown by default again.

## \[0.0.14\] - 2025-01-30

### Fixed

- Correctly consume bfabricPy from PyPI.

## \[0.0.13\] - 2025-01-28

### Added

- `WorkunitDefinition.registration.workunit_name` field.

## \[0.0.12\] - 2025-01-22

## Added

- New input type `bfabric_order_fasta` which will place an order fasta file to the specified path, or create an empty
    file if there is no order fasta available.
- `--filter` flag has been added to `inputs prepare` and `inputs clean` commands.
- The `app-runner app` commands now support passing a `AppVersion` yaml file instead of just a `AppSpec` yaml file.

## \[0.0.11\] - 2025-01-16

### Added

- New input type `BfabricAnnotationSpec`.
    - For now, it only supports one type of annotation, which is `"resource_sample"`.

## \[0.0.10\] - 2025-01-15

### Added

- `FileScpSpec` to copy a file from a remote server to the local filesystem, without using B-Fabric information.
- `CommandDocker.hostname` so it won't have to be passed by `custom_args` in the future.
- `DispatchSingleDatasetFlow` dispatch a workunit in dataset-flow which consists of only one execution unit.
- `DispatchSingleResourceFlow` dispatch a workunit in resource-flow which consists of only one execution unit.

## \[0.0.9\] - 2025-01-09

### Added

- App specs can now define multiple versions in one file. (AppSpec = Collection of app versions and other information.)
    - To avoid boilerplate, mako templates can be used inside of strings.
    - Apps will resolve the version to use based on the `application_version` field.
    - Validation functionality for the new app specification has been added.
- App versions can define a submitter, however this information is not yet used.

## \[0.0.8\] - 2025-01-08

### Added

- Register single file command: `bfabric-app-runner outputs register-single-file`
- Implement copy resource `UpdateExisting.IF_EXISTS` and `UpdateExisting.REQUIRED` support.
- The following fields have been added to `WorkunitRegistrationDefinition`:
    - `storage_id`
    - `storage_output_folder`
    - `application_id`
    - `application_name`

### Changed

- App-runner code related to output staging accepts workunit-definition file like the other steps.

## \[0.0.7\] - 2024-11-22

### Fixed

- When executing `app run` the experimental entity cache created incorrect behavior. The caching is temporarily disabled,
    until the issue is resolved.

## \[0.0.6\] - 2024-11-14

First version with CD that will trigger the deployment automatically.

### Fixed

- Output spec was broken since `Path` was moved into `if TYPE_CHECKING` block.

### Changed

- The app spec is now strict and will fail parsing if there are any unknown fields in the spec. It is better to find
    this type of error early.
- Log messages originating in `app_runner` should be printed now, they were previously muted (unintentionally).

## \[0.0.5\] - 2024-11-11

### Added

- `CommandDocker.mac_address`: allows to specify the MAC address of the container.
- `CommandDocker.custom_args`: allows to specify arbitrary additional arguments to the `docker run` command.

## \[0.0.4\] - 2024-11-11

### Added

- `MountOptions.writeable` list for writeable mount points.

## \[0.0.3\] - 2024-10-24

### Added

- Specify environment variables for docker container in spec.

## \[0.0.2\] - 2024-10-23

### Added

- App spec supports changing docker entrypoint.
- `bfabric-app-runner inputs check` to validate the local files

### Fixed

- `bfabric-app-runner inputs list` does not fail anymore if resources have no "name" field value.

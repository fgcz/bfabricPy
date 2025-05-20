# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## \[Unreleased\]

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

- Silence interpolate_config_strings log messages.
- Update `bfabric` dependency to 1.13.26.
- App versions do not always require a version key as it will default to "latest", but only one version can have a
    particular version key per app definition.

### Fixed

- Use most recent cyclopts version again, i.e. [issue 168](https://github.com/fgcz/bfabricPy/issues/168) is fixed.

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

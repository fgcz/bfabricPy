# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## \[Unreleased\]

### Added

- Implement `--force-storage` to pass a yaml to a forced storage instead of the real one.

### Changed

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

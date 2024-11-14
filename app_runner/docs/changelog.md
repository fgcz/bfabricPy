# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## \[Unreleased\]

## \[0.0.6\] - 2024-11-14

First version with CD that will trigger the deployment automatically.

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

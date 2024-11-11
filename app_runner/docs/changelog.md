# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## \[Unreleased\]

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

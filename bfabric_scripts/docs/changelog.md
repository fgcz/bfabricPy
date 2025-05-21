# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Versioning currently follows `X.Y.Z` where

- `X` is used for major changes, that contain breaking changes
- `Y` should be the current bfabric release
- `Z` is increased for feature releases, that should not break the API

## \[Unreleased\]

## \[1.13.28\] - 2025-05-21

### Removed

- Removed `bfabric_delete.py`. Use `bfabric-cli api delete` instead.
- Removed `bfabric_list_not_available_proteomics_workunits.py`. Use `bfabric-cli workunit not-available` instead.

### Changed

- Update `bfabric` to 1.13.27.
- `bfabric-cli api delete` will use the type of the entity in CLI messages.

## \[1.13.27\] - 2025-04-22

### Changed

- `bfabric-cli dataset upload` will print warnings when trailing whitespace is detected and not print the whole
    response anymore, but rather the important information only.

### Added

- Optional support for uploading xlsx (currently behind `excel` optional feature).

## \[1.13.26\] - 2025-04-08

### Changed

- Update `bfabric` to 1.13.24.

### Removed

- Remove `bfabric-cli api save` -> use `bfabric-cli api create` and `bfabric-cli api update` instead.

### Fixed

- Use most recent cyclopts version again, i.e. [issue 168](https://github.com/fgcz/bfabricPy/issues/168) is fixed.

## \[1.13.25\] - 2025-03-27

### Fixed

- Temporary workaround for https://github.com/fgcz/bfabricPy/issues/168.

## \[1.13.24\] - 2025-02-19

### Fixed

- Update `bfabric` to 1.13.22 for dataset fix.

## \[1.13.23\] - 2025-02-19

### Added

- `bfabric-cli dataset {upload, download, show}` to replace the old dataset-related scripts.
- `bfabric-cli api update` command to update an existing entity
- `bfabric-cli api create` command to create a new entity
- `bfabric-cli api delete` command to delete an existing entity

## \[1.13.22\] - 2025-02-17

### Fixed

- Fix printing of YAML for parsing with shyaml, previously line breaks could have been introduced.

## \[1.13.21\] - 2025-02-11

### Fixed

- Add missing default value for columns in `bfabric-cli api read`

## \[1.13.20\] - 2025-02-10

### Added

- `bfabric-cli workunit not-available`:
    - allows sorting by arbitrary fields, e.g. application id
    - allows filtering inclusive or exclusive by user

### Changed

- Pin bfabricPy version to avoid future headaches.
- `bfabric-cli api read`
    - Removes the automatic output type logic
    - Multiple values can be submitted for the same key (just specify it multiple times)
    - The actual query will be printed as a line of bfabricPy code
    - `--file` parameter to write the output to a specific file
    - Argument parsing is handled with pydantic now
    - Added tsv support

## \[1.13.19\] - 2025-01-29

Initial release of standalone bfabric_scripts package.

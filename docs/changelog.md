# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Versioning currently follows `X.Y.Z` where

- `X` is used for major changes, that contain breaking changes
- `Y` should be the current bfabric release
- `Z` is increased for feature releases, that should not break the API

## \[Unreleased\]

### Changed

- The submitter ensures that workunits always get set to `processing`.

## \[1.13.11\] - 2024-12-13

### Fixed

- The script `bfabric_setWorkunitStatus.py` did always set the status to `available`, instead of the specified status.

### Changed

- `bfabric_setResourceStatus_available.py` calls the `report_resource` function, in general this functionality has been refactored.

## \[1.13.10\] - 2024-12-13

### Fixed

- If `bfabricpy.yml` contains a root-level key which is not a dictionary, a correct error message is shown instead of raising an exception.
- A bug introduced while refactoring in `slurm.py` which passed `Path` objects to `subprocess` instead of strings.
- Submitter
    - does not use unset `JOB_ID` environment variable anymore.
    - does not set unused `STAMP` environment variable anymore.
- Fix `bfabric_save_workflowstep.py` bugs from refactoring.

### Added

- Experimental bfabric-cli interface. Please do not use it in production yet as it will need a lot of refinement.

## \[1.13.9\] - 2024-12-10

From this release onwards, the experimental app runner is not part of the main bfabric package and
instead a separate Python package with its individual changelog.

### Added

- Relationship: `ExternalJob.executable`
- (experimental) EntityLookupCache that allows to cache entity lookups in a script to avoid redundant requests.
- Specific use case script: bfabric_save_resource_description.py (the functionality will be available in a future CLI).

### Fixed

- `Entity.find_all` returns no values when an empty list is passed as an argument.

### Changed

- Except for macOS x86_64 (which we assume is Rosetta emulation nowadays), we use the faster `polars` instead of `polars-lts-cpu`.
- `BfabricRequestError` is now a `RuntimeError` subclass.
- Add `py.typed` marker.

### Removed

- `bfabric_legacy.py` has been removed.
- `math_helper.py` has been removed.

## \[1.13.8\] - 2024-10-03

This release contains mainly internal changes and ongoing development on the experimental app interface functionality.

### Added

- Entities can be compared and sorted by ID now.
- Show Python version in version info string.
- Caching for bfabric_list_not_existing_storage_directories.py.
- (experimental) add initial code for a resource based application dispatch
- (experimental) new app_runner cli that integrates all commands into a single interface

### Fixed

- bfabric_read.py is a bit more robust if "name" misses and tabular output is requested.

### Changed

- `bfabric.scripts` has been moved into a namespace package `bfabric_scripts` so we can later split it off.
- (internal) migrate to src layout
- (experimental) the former `process` step of the app runner has been split into a `process` and `collect` step where,
    the collect step is responsible for generating the `output.yml` file that will then be used to register the results.
- (experimental) app runner apps by default reuse the default resource

## \[1.13.7\] - 2024-09-17

### Fixed

- `bfabric_save_csv2dataset.py` considers all rows for schema inference, only considering the first 100 rows did cause problems with some files previously.

### Added

- Script logging configuration
    - If `BFABRICPY_DEBUG` environment variable is set, log messages in scripts will be set to debug mode.
    - Log messages from `__main__` will also be shown by default.
- `bfabric.entities.MultiplexKit` to extract multiplex kit information.
- `bfabric.entities.Workunit.store_output_folder` implements the old rule, but more deterministically and reusable.
- (Experimental) `bfabric.experimental.app_interface` core functionality is implemented
    - This can be used as a building block to standardize the input preparation for applications.

### Changed

- Correctly support optional workunit parameters.

### Removed

- `bfabric.entities.Resource` association `application` has been removed as it does not exist

## \[1.13.6\] - 2024-08-29

### Added

- `Entity.find_by` has new parameter `max_results`.

### Changed

- `bfabric_read.py` prints non-output information exclusively through logger and does not restrict entity types anymore.
- `bfabric_delete.py` accepts multiple ids at once and does not restrict entity types anymore.
- Both engines raise a `BfabricRequestError` if the endpoint was not found.

### Removed

- `bfabric.endpoints` list is deleted, since it was out of date and generally not so useful.

## \[1.13.5\] - 2024-08-13

### Added

- The `Bfabric` instance is now pickleable.
- Entities mapping:
    - Add `Entity.id` and `Entity.web_url` properties.
    - Add `Entity.__getitem__` and `Entity.get` to access fields from the data dictionary directly.
    - Add `Entity.find_by` to find entities by a query.
    - More types and relationships
    - Relationships defer imports to descriptor call, i.e. circular relationships are possible now.
    - `HasOne` and `HasMany` allow defining `optional=True` to indicate fields which can be missing under some circumstances.
- Add `nodelist` column and application name to `bfabric_list_not_available_proteomics_workunits.py` output.

### Changed

- `Entity.find_all` supports more than 100 IDs now by using the experimental MultiQuery API.

## \[1.13.4\] - 2024-08-05

### Added

- Add `Workunit`, `Parameter`, and `Resource` entities.
- Add concept of has_many and has_one relationships to entities.
- `bfabric_slurm_queue_status.py` to quickly check slurm queue status.
- `Bfabric.save` provides `method` which can be set to `checkandinsert` for specific use cases.

### Changed

- Most messages are now logged to debug level.
- The old verbose version information is now always logged, to INFO level, since it could entail useful information for error reporting.

## \[1.13.3\] - 2024-07-18

### Added

- Flask
    - New endpoint `GET /config/remote_base_url` for testing

### Changed

- Flask
    - Simplify logging by using loguru only.
    - Simplified setup logic since the production use case should use a WSGI server.

### Fixed

- `bfabric_save_csv2dataset.py` had an undeclared dependency on numpy and a few bugs which was improved.

## \[1.13.2\] - 2024-07-11

### Added

- Add `bfabric.entities.Dataset` to easily read datasets.
- Pydantic-based configuration parsing
    - The config format did not change.
    - The code is easier to maintain now.
    - Additionally, there is a lot more validation of the configuration file now, that should catch errors early.
- Make host and port configurable in `bfabric_flask.py` (currently only dev mode).

## \[1.13.1\] - 2024-07-02

### Changed

- bfabric_save_csv2dataset will raise an error if problematic characters are found in any of the cells
- Correctly define `bfabric_setWorkunitStatus_available.py`, and `processing` and `failed` variants.

### Added

- Add loguru for future logging refactoring.
- Easily runnable tests with `nox` and standardized formatting using `pre-commit`.

### Removed

- Pandas is no longer a dependency, and has been replaced by polars.

## \[1.13.0\] - 2024-05-24

This is a major release refactoring bfabricPy's API.

### Changed

- The `Bfabric` class operations now return `ResultContainer` objects.
    - These provide a list-like interface to access individual items or iterate over them.
    - Individual items are a dictionary, potentially nested, and not specific to suds/zeep anymore.
    - Convenience conversions, e.g. to a polars DataFrame, can be provided there.
- Configuration is now defined in `~/.bfabricpy.yml` and supports multiple configurations, which can be selected by the `BFABRICPY_CONFIG_ENV` environment variable. Please consult the README for an example configuration.
- Use `pyproject.toml` for package configuration.
- Scripts have been refactored on a case-by-case basis.

### Added

- Zeep can be used instead of suds for SOAP communication.
- `Bfabric` can be instantiated without authentication, that can be provided later. This is useful in a server setup.
- Pagination support in `Bfabric`, specify the number of max_results and a potential offset. Pages handling is abstracted away.
- Detect errors in responses, e.g. invalid login.

### Removed

- Several old scripts have been moved into a `deprecated_scripts` folder.
- Wrapper creator related code is currently not updated but has been extracted into a dedicated folder `wrapper_creator` as well.

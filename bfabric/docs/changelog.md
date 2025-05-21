# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Versioning currently follows `X.Y.Z` where

- `X` is used for major changes, that contain breaking changes
- `Y` should be the current bfabric release
- `Z` is increased for feature releases, that should not break the API

## \[Unreleased\]

## \[1.13.27\] - 2025-05-21

### Added

- Attribute `Bfabric.config_data` to obtain a `ConfigData` object directly.
- `TokenData.load_entity` convenience method to load an entity from the token data.
- Entities `Instrument`, `Plate`, `Run` were added (but with no extra functionality).
- `Workunit.{application_parameters, submitter_parameters}` to access parameter values.

### Changed

- Submitter parameters will not be written any longer to `WorkunitExecution` parameters.

### Fixed

- Compatibility with upcoming change that `Application` can have multiple `technology` values.

### Deprecated

- `Workunit.parameter_values` will be removed in favor of `Workunit.application_parameters` and `Workunit.submitter_parameters` in a future version.

## \[1.13.26\] - 2025-04-26

This release introduces an environment variable `BFABRICPY_CONFIG_OVERRIDE` to configure the `Bfabric` client completely,
along with a new method for creating an instance of the `Bfabric` client, `Bfabric.connect()`.
This will allow us to propagate any configuration to subprocesses reliably. `BFABRICPY_CONFIG_ENV` remains available
with the same semantics, but lower priority than `BFABRICPY_CONFIG_OVERRIDE`.

This also simplifies the logic that was present in `Bfabric.from_config` which is why this introduced with a new API
to prevent configuration mix-ups.

### Added

- New environment variable `BFABRICPY_CONFIG_OVERRIDE` to configure the `Bfabric` client completely
- New method `Bfabric.connect()` for creating an instance of the `Bfabric` client

### Changed

- Renamed `Bfabric.from_token` to `Bfabric.connect_webapp()` (along with some changes, no known users of this API yet)
- Disallowed `default` as an environment config name
- `bfabric.cli_integration.utils.use_client` uses `Bfabric.connect()` instead of `Bfabric.from_config()`

### Deprecated

- `Bfabric.from_config` is now deprecated in favor of `Bfabric.connect()`

## \[1.13.25\] - 2025-04-22

### Breaking

- `Bfabric.from_token` returns the `TokenData` in addition to the client instance. While this is breaking, I'm not aware
    of any existing users of this API and I noticed that this information is going to be needed in this context often.

### Added

- `bfabric.experimental.upload_dataset.warn_on_trailing_spaces` function used by `bfabric-scripts` to validate

## \[1.13.24\] - 2025-04-08

### Removed

- `cyclopts` is not a dependency of `bfabric` anymore, but rather of `bfabric-scripts` and `bfabric-app-runner`.

### Changed

- `Bfabric` client now does not take `engine` argument anymore, but rather this information comes from `ClientConfig`.
    For compatibility reasons, the `engine` argument is still accepted in `Bfabric.from_config` and
    `Bfabric.from_token`.

## \[1.13.23\] - 2025-03-25

### Fixed

- Unsuccessful deletions are detected by checking the B-Fabric response.
- Handle problematic characters in `Workunit.store_output_folder`.
- `BfabricRequestError` did not properly subclass RuntimeError.

### Changed

- `WorkunitDefinition` uses `PathSafeStr` to normalize app and workunit names.
- Internal: `ResultContainer` has no optional constructor arguments anymore to avoid confusion.

### Added

- Generic functionality in `bfabric.utils.path_safe_name` to validate names for use in paths.
- `bfabric.entities.Dataset.{write_parquet, get_parquet}` methods for writing parquet

## \[1.13.22\] - 2025-02-19

### Fixed

- Correctly read datasets, if columns were swapped in B-Fabric.

### Changed

- `Dataset.types` was renamed to `Dataset.column_types`, since there is only 1 usage and it is recent, this is not considered breaking.

## \[1.13.21\] - 2025-02-19

### Added

- `Entity.load_yaml` and `Entity.dump_yaml`
- `Bfabric.from_token` to create a `Bfabric` instance from a token
- `bfabric.rest.token_data` to get token data from the REST API, low-level functionality

### Changed

- Internally, the user password is now in a `pydantic.SecretStr` until we construct the API call. This should prevent some logging related accidents.

## \[1.13.20\] - 2025-02-10

### Breaking

- the old `bfabric.cli_formatting` and `bfabric.bfabric2` modules have been deleted

### Changed

- move `use_client` to `bfabric.utils.cli_integration`: this will allow reuse between bfabric-scripts and bfabric-app-runner
- move functionality from `bfabric.cli_formatting` to `bfabric.utils.cli_integration`

## \[1.13.19\] - 2025-02-06

### Fixed

- Config: Log messages of app runner are shown by default again.

## \[1.13.18\] - 2025-01-28

### Changed

- `bfabric_upload_resource.py` does not print a list anymore, but rather only the dict of the uploaded resource.

### Fixed

- Some scripts were not Python 3.9 compatible, which is restored now. However, we can consider increasing the Python requirement soon.

## \[1.13.17\] - 2025-01-23

### Added

- `bfabric-cli workunit export-definition` to export `workunit_definition.yml` files
- `Executable.storage` relationship

### Fixed

- `Workunit.parameters` and `Workunit.resources` are optional
- `bfabric-cli` had unmet dependencies, that were not caught by the tests either

## \[1.13.16\] - 2025-01-22

### Added

- Add missing `Entity.__contains__` implementation to check if a key is present in an entity.
- `polars_utils.py` which contains functionality to normalize relational fields in tables
- Add `bfabric-cli executable inspect` command to inspect executables registered in B-Fabric.
- Add `bfabric-cli executable upload` command to upload executables to B-Fabric.

### Fixed

- `Order.project` is optional

## \[1.13.15\] - 2025-01-15

### Added

- Entity `Sample`
- Relationship `Resource.sample`.
- Extract logic for container resolution into `HasContainerMixin` which is right now shared between `Sample` and `Workunit`.

### Fixed

- Fix bug in `bfabric_save_fasta.py`.

## \[1.13.14\] - 2025-01-08

### Changed

- Slurm submitter prints more diagnostics about PATH variable etc.

### Fixed

- Some commands in bfabric-cli are broken because `__future__.annotations` is imported and this breaks cyclopts.

## \[1.13.13\] - 2024-12-18

### Changed

- Move `bfabric-cli read` to `bfabric-cli api read`.
- (internal) `use_client` decorator is introduced to simplify and standardize the client usage in the new CLI code.

### Added

- Functionality to log by specifying the workunit instead of external job, which is used in some legacy scripts.
- Add logging commands to `bfabric-cli api log`.
- Add `bfabric-cli api save`.
- Submitter script prints the id and hostname of apps, which in practice can be very useful.

### Fixed

- A bug in bfabric_save_workflowstep.py that crashed the script.

## \[1.13.12\] - 2024-12-17

### Changed

- The submitter ensures that workunits always get set to `processing`.

### Fixed

- The script `bfabric_setResourceStatus_available.py` and other uses of `report_resource`, correctly search files which
    have a relative path starting with `/` as in the case of the legacy wrapper creator.

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

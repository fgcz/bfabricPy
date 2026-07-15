# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Versioning currently follows `X.Y.Z` semantic versioning, independent of the `bfabric` core package version:

- `X` is used for major changes, that contain breaking changes
- `Y` is increased for feature releases, that should not break the API
- `Z` is increased for bug-fix releases

## \[Unreleased\]

## \[1.16.0rc2\] - 2026-07-15

- `bfabric-cli auth` command group for OAuth authentication and client management:
    - Login: `auth pkce` (browser), `auth device-code` (headless), `auth pat` (Personal Access Token).
    - `auth register` / `auth register-webapp` — dynamic client registration, optionally with a linked B-Fabric app.
    - `auth default [CONFIG_ENV]` — set the default environment; an arrow-key interactive picker (navigate the list or type to filter, Enter to select; each row shows the host and auth method) opens when no value is given, or lists the environments in a non-interactive context.
    - `auth status` and `auth logout`.
    - `auth pat` stores the token under a `pat` key with `auth_method: pat` (not `login: __oauth__` / `password:`), keeping the shared config parseable by older (≤1.19.0) clients; `auth status` reports these as `pat`.
- `bfabric-cli workunit upload FILES...` — upload files and directories to a workunit over tus (resumable, large-file capable), creating a new workunit or targeting `--workunit-id`. One resource per file, skips duplicates (unless `--force`), expands directories, live progress (`--no-progress`); `--track-job` records an `UPLOAD` job. Requires an OAuth client with the `tus` scope.
- `bfabric-cli api create` / `api update` accept `--format json|yaml|tsv|table_rich` (default `json`), matching `api read`.
- `bfabric-cli dataset update` — update an existing dataset with a change preview before confirming (`csv`/`tsv`/`xlsx`/`parquet`, same validation flags as `dataset upload`).
- `api create` / `api update` now emit valid JSON (was Python `repr` via `rich.pretty.pprint`, breaking `jq`) and serialise `datetime` / `Decimal` to strings instead of raising `TypeError` ([#503](https://github.com/fgcz/bfabricPy/issues/503)).
- Internal: `dataset upload` and `bfabric_save_csv2dataset.py` now use `bfabric.operations.dataset.create_dataset`; API error handling is centralized in `@use_client` (no more `@logger.catch`); `--config-env` naming unified. Declares `lxml` as an explicit dependency (was transitive via the now-optional `zeep`) and requires `bfabric[transfer]` >= 1.20 (for `upload_files` / tus). Adds `questionary` for interactive CLI prompts, wrapped in a reusable `cli.interactive` helper (`resolve_choice` / `select_choice` / `select_or_input`).

## \[1.15.0\] - 2026-04-20

### Added

- All scripts decorated with `use_client` now accept `--config-env` and `--config-file` flags, making it more reliable to target a particular bfabric instance.
- `bfabric-cli dataset download` supports `excel` format (`.xlsx`) via the `excel` extra.

### Changed

- `bfabric-cli dataset download` now defaults to `auto` format, inferring the output format from the file extension.
- Use `hashlib.file_digest` for checksum computation ([#349](https://github.com/fgcz/bfabricPy/issues/349)).

### Fixed

- `PathConventionMS` now handles instruments with a number in the name before the underscore character.

## \[1.14.0\] - 2026-03-12

### Added

- `bfabric-cli api read` now supports `--return-id-only` flag to return only entity IDs instead of full data, which is faster for large queries.

### Changed

- `bfabric-cli api read` and `bfabric-cli executable upload` diagnostic/informational output is now routed through loguru, so it can be silenced via `BFABRICPY_LOG_LEVEL=OFF` (or `WARNING`/`ERROR`/`CRITICAL`).

## \[1.13.40\] - 2025-12-16

### Added

- `bfabric-cli api inspect` to inspect various API endpoints directly from the command line.

## \[1.13.39\] - 2025-12-03

### Fixed

- Fix bfabric_read_samples_of_workunit.py returns the same column name `groupingvar_name` as in the past.

## \[1.13.38\] - 2025-12-03

### Changed

- Minimal Python version is now 3.11.
- `bfabric_flask` validate_token uses the newer functionality in bfabricPy.
- Update `bfabric` dependency to `>=1.14.1,<1.15.0`.

### Fixed

- Fix bfabric_read_samples_of_workunit.py ordering.

## \[1.13.37\] - 2025-10-27

### Changed

- Last version to support Python 3.10, next version will require Python 3.11 or higher.
- Upper bounds for dependencies have been introduced.
- Update `bfabric` to `1.13.36`.
- Update `cyclopts` to `4.*`

## \[1.13.36\] - 2025-10-13

### Removed

- Delete unused `bfabric_feeder_resource_autoQC.py` script.

### Fixed

- `bfabric_save_importresource_sample.py` sample ID detection has been updated to work with recent queue generator and enabled for metabolomics.

### Changed

- `bfabric_flask.py` didn't log exceptions properly because it passed the wrong argument `exc_info` instead of `exception`.
- Legacy: `bfabric_save_workflowstep.py` reads config from `~/slurmworker/config/legacy_template_steps.yml`. Not relevant for bfabric-app-runner apps.

## \[1.13.35\] - 2025-09-25

### Changed

- `bfabric_list_not_existing_storage_directories.py` is made more robust. Instead of the file based cache, it will check all containers modified within a sliding time window (default 14 days).

## \[1.13.34\] - 2025-09-22

### Fixed

- `bfabric_save_importresource_sample.py` now properly serializes ResultContainer objects for JSON output.

### Changed

- Update `bfabric` to include case-insensitive dataset column type detection support.

## \[1.13.33\] - 2025-08-26

### Changed

- Update `bfabric` to 1.13.32.

## \[1.13.32\] - 2025-08-20

### Fixed

- Legacy `bfabric_save_workflowstep.py` is compatible with current bfabricPy version again.

### Changed

- Update `bfabric` to 1.13.31.

## \[1.13.31\] - 2025-08-19

### Fixed

- `bfabric-cli api read` handles empty results gracefully for all output formats.

### Changed

- Update `bfabric` to 1.13.30. This includes a fix for legacy wrapper creator.

## \[1.13.30\] - 2025-07-04

### Added

- `bfabric_flask.py` provides support for token-based authentication for B-Fabric.

### Removed

- `bfabric_flask.py` is not exported as a script anymore, because misuse can lead to security issues and should be deployed properly.

## \[1.13.29\] - 2025-06-27

### Removed

- Deprecated `bfabric-cli api log` subcommand was removed.

### Added

- `bfabric-cli executable dump` command to export YAML and XML of executables
- `bfabric-cli feeder create-importresource` command to register importresource objects in B-Fabric
- `bfabric-cli executable upload` supports XML

### Fixed

- `bfabric-cli workunit not-available` shows nodelist for workunits using new submitter.

### Changed

- Columns of tables named after B-Fabric entities, containing only integers, will be set as the specified type
    when saving to B-Fabric.
- Update `bfabric` to 1.13.28.
- Update legacy `bfabric_logthis.py`, the workunit target logic has been removed (unused).

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

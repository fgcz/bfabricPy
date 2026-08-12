# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Versioning currently follows `X.Y.Z` semantic versioning, independent of the `bfabric` core package version:

- `X` is used for major changes, that contain breaking changes
- `Y` is increased for feature releases, that should not break the API
- `Z` is increased for bug-fix releases

## \[Unreleased\]

### Added

- `bfabric-cli login` renews an expired token with **no arguments** — instance URL and scope are read back from the environment; a first login picks the instance from the known hosts and derives the environment name. Also a top-level shortcut for `auth login`.
- `auth login --no-browser` prints the authorization URL instead of opening a browser (local machines only — over SSH use `auth device-code`).
- `auth register` / `register-webapp` gain `--no-service-user`, and `--service-user` no longer silently defaults to "none": omitting it by accident (registering a client without the `client_credentials` grant) now fails fast.
- New user guide: [Authentication](https://fgcz.github.io/bfabricPy/user_guides/bfabric-cli/authentication.html) — command surface, scopes, logout vs remove, remote hosts.

### Changed

- `auth default` is now `auth activate` (no alias). `auth logout` no longer deletes the environment — it clears only this machine's credentials (cached OAuth token, inline `pat` or `login`+`password`), leaving it ready for a zero-argument re-login; `--all` covers every environment, and the old behaviour is `auth remove`. It does not revoke the token server-side, which it now says.
- `auth list` groups environments by instance and shows scope and token expiry; `list` and `status` mark *why* an environment is the active one.
- Every `auth` command resolves the environment as `--config-env` > `BFABRICPY_CONFIG_ENV` > the configured default, and commands that write the config refuse to run under `BFABRICPY_CONFIG_OVERRIDE`.
- Re-pointing an environment at a different instance URL needs confirmation, and is refused non-interactively.
- Base URLs are normalised up front: scheme defaulted, host lowercased, trailing slash dropped, bare known hosts expanded, non-http(s) rejected.
- `workunit upload --force` is replaced by `--on-duplicate upload|skip|link`, and `upload` is the new default — the duplicate check no longer runs unless asked for, so a re-upload of content the container already holds transfers it again. Pass `skip` for the old behaviour, or `link` to give the workunit a resource pointing at the already-stored bytes instead of omitting the file.
- Packaging: `project.readme` points at the package's own `README.md` (same hatchling 1.32.0 constraint as `bfabric`); the README was expanded into a proper landing page, since it is what PyPI shows.
- Internal: login handlers normalised to `cmd_auth_*`; shared resolution in `cli/login/_common.py`, base-URL handling in a new `_urls.py`; `auth register` obtains its bearer token via `Bfabric.connect()` instead of rebuilding the credential-provider and token-cache lookup itself.

### Fixed

- `auth register-webapp` prints a clean `Error: ...` and exits 1 when the OAuth session cannot be refreshed (e.g. an expired/revoked refresh token), instead of a raw traceback.
- `auth register` no longer prompts for an *Employee Bearer token* when a login already exists: with neither `--token` nor `--config-env` it authenticates as the environment in effect, so `auth login` followed by `auth register` just works. Pass `--token` to supply one explicitly.

## \[1.16.0\] - 2026-08-03

- `bfabric-cli auth` — OAuth authentication & client management. Login: `login` (browser), `device-code` (headless), `pat`; client registration: `register` / `register-webapp`; environment management: `default`, `list`, `status`, `logout`. Scope presets (`read-only` / `read-write` / `upload`) or a raw scope, via an interactive picker when `--scope` is omitted in a terminal; no baked-in default scope, so a headless run must pass `--scope` (registration keeps the OIDC-inclusive default webapps need). When `--config-env` is omitted it prompts for the environment (else targets the current default / `PRODUCTION`); unless `--set-default` / `--no-set-default` is given it asks (default yes) whether to make the env the default, and cancelling that prompt aborts the login. `status` reports an OAuth env's cached-token freshness and granted scope (annotated with the matching preset); `logout` removes an env's config entry and cached tokens (confirmation required). PATs are stored under a `pat` key (`auth_method: pat`), keeping the config parseable by ≤1.19.0 clients.
- `bfabric-cli workunit upload FILES...` — upload files/directories to a workunit over tus (resumable, large-file capable): new or `--workunit-id`, one resource per file, skips duplicates (`--force`), live progress (`--no-progress`), optional `--track-job`. Requires an OAuth client with the `tus` scope.
- `bfabric-cli workunit diff REF1 REF2` — compare two workunits side by side (name, parameters, output/input resources, status, application, container, input dataset), highlighting differences in rich tables. Each reference is a numeric workunit ID or a workunit URL, including one copied straight from the browser (extra query parameters such as `&tab=details` are accepted); `--only-diff` collapses the output to just the differing rows.
- `bfabric-cli api create` / `api update` — accept `--format json|yaml|tsv|table_rich` (default `json`); now emit valid JSON and serialise `datetime` / `Decimal` (was Python `repr`, breaking `jq`) ([#503](https://github.com/fgcz/bfabricPy/issues/503)).
- `bfabric-cli dataset update` — update an existing dataset with a change preview before confirming (`csv`/`tsv`/`xlsx`/`parquet`).
- Internal: `dataset upload` / `bfabric_save_csv2dataset.py` use `bfabric.operations.dataset.create_dataset`; API error handling centralized in `@use_client` (dropped `@logger.catch`); `--config-env` naming unified; `lxml` now an explicit dep (was transitive via optional `zeep`); requires `bfabric[transfer]>=1.20`; adds `questionary`-based `cli.interactive` helpers and `config_writer.remove_environment_from_config`.

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

# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## \[Unreleased\]

### Added

- Initial implementation of bfabric_rest_proxy.
- `POST /user/is_employee` — returns `{"is_employee": bool}` for the authenticated user based on their `empdegree` field. The lookup uses the feeder credentials, since `empdegree` is typically not readable with a regular user's web-service credentials.
- `POST /create/workunit/v1` accepts optional `dataset` (name + base64-encoded csv/tsv/parquet, created as the workunit's output dataset) and `input_dataset_id` (existing dataset referenced as the workunit's input), both inherited from `CreateWorkunitParams`.
- `POST /create/workunit/v1` accepts optional `executables` (name → base64-encoded content), attached to the created workunit, inherited from `CreateWorkunitParams`.
- `POST /create/workunit/v1` accepts an optional `created_using` field (e.g. calling-app identifier), recorded as the `Created Using` custom attribute alongside the server-stamped `Created For` attribute.

### Changed

- `feeder_operations.create_workunit` is a thin authorization + audit-stamping wrapper around `bfabric.operations.workunit.create_workunit`, taking a single `CreateWorkunitRequest`. A failure after initial creation now flips the workunit to status `failed` instead of orphaning it in `processing`.
- Renamed the workunit custom attribute that records the initiating web-app user from `WebApp User` to `Created For`.
- Require `fastapi>=0.134.0` (was `>=0.124.0`) so the transitive `starlette` dependency resolves to `>=1.0.1` ([#505](https://github.com/fgcz/bfabricPy/issues/505)).

### Fixed

- `/validate_token` uses the server-configured `validation_bfabric_instance` instead of the client-provided instance.
- An empty list `[]` query parameter from R clients is handled (converted to an empty dict `{}`).
- A `bfabric_instance` request parameter is canonicalised before it is matched against `supported_bfabric_instances`, so a trailing slash no longer makes a configured instance look unknown. `default_bfabric_instance` and the `feeder_user_credentials` keys are canonicalised the same way at startup.
- `default_bfabric_instance: null`, documented as making the `bfabric_instance` parameter mandatory, no longer fails settings validation.

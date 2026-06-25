# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## \[Unreleased\]

### Changed

- `feeder_operations.create_workunit` is now a thin authorization + audit-stamping wrapper around `bfabric.operations.workunit.create_workunit`. The workunit creation now flips the workunit to status `failed` on any error after initial creation (was: orphaned in `processing` status).
- `POST /create/workunit/v1` request body now accepts an optional `created_using` field (e.g. calling-app identifier). It is recorded as the `Created Using` custom attribute alongside the server-stamped `Created For` attribute. The wrapper signature changed accordingly: it now takes a single `CreateWorkunitRequest` (subclass of `CreateWorkunitParams`) instead of separate `params` + `created_using` arguments.
- Renamed the workunit custom attribute that records the initiating web-app user from `WebApp User` to `Created For`.
- Resolve the authenticated user via `Bfabric.current_identity` instead of `auth.login`, so `Created For`, `/user/is_employee`, and request logs name the real user under OAuth.

### Fixed

- `/validate_token` now uses the server-configured `validation_bfabric_instance` instead of the client-provided instance.
- Handle empty list `[]` query parameter from R clients (converts to empty dict `{}`).

### Added

- `POST /user/is_employee` endpoint: returns `{"is_employee": bool}` for the authenticated user based on their `empdegree` field. The user record lookup is performed with the feeder credentials, since `empdegree` is typically not readable with a regular user's web-service credentials.
- Initial implementation of bfabric_rest_proxy.

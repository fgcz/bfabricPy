# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## \[Unreleased\]

### Fixed

- `/validate_token` now uses the server-configured `validation_bfabric_instance` instead of the client-provided instance.
- Handle empty list `[]` query parameter from R clients (converts to empty dict `{}`).

### Added

- `POST /user/is_employee` endpoint: returns `{"is_employee": bool}` for the authenticated user based on their `empdegree` field.
- Initial implementation of bfabric_rest_proxy.

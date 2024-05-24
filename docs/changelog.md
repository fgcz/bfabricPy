# Changelog
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Versioning currently follows `X.Y.Z` where

- `X` is used for major changes, that contain breaking changes
- `Y` should be the current bfabric release
- `Z` is increased for feature releases, that should not break the API

## [1.13.0] - 2024-05-24
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

### Removed
- Several old scripts have been moved into a `deprecated_scripts` folder.

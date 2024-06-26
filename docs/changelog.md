# Changelog
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Versioning currently follows `X.Y.Z` where

- `X` is used for major changes, that contain breaking changes
- `Y` should be the current bfabric release
- `Z` is increased for feature releases, that should not break the API

## [tba] - tba


## [1.13.1] - 2024-07-02
### Changed
- bfabric_save_csv2dataset will raise an error if problematic characters are found in any of the cells
- Correctly define `bfabric_setWorkunitStatus_available.py`, and `processing` and `failed` variants.

### Added
- Add loguru for future logging refactoring. 
- Easily runnable tests with `nox` and standardized formatting using `pre-commit`.

### Removed
- Pandas is no longer a dependency, and has been replaced by polars.

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
- Pagination support in `Bfabric`, specify the number of max_results and a potential offset. Pages handling is abstracted away.
- Detect errors in responses, e.g. invalid login.

### Removed
- Several old scripts have been moved into a `deprecated_scripts` folder.
- Wrapper creator related code is currently not updated but has been extracted into a dedicated folder `wrapper_creator` as well.

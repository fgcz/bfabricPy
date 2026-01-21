# BFabric App Configuration

This document describes how to specify a bfabric-app-runner application in an app.yml file. This file is understood by the bfabric-app-runner submitter integration in B-Fabric, and the path to it is specified as the "program" in the b-fabric executable.

## Configuration Structure

The configuration is defined in YAML format with the following main sections:

### App Runner Version

```yaml
bfabric:
  app_runner: 0.2.1
```

The `app_runner` version (e.g., `0.2.1`) specifies which version to pull from PyPI.

### Application Versions

Multiple application versions can be defined, each with their own command definitions. The version can be specified in bfabric with the `application_version` key parameter.

#### Release Versions

The YAML defines versions of the application, where each version identifier should be unique. To avoid configuration duplication, multiple versions can use the same definition with template variables available:

```yaml
versions:
  - version:
      - 4.7.8.dev3
      - 4.7.8.dev4
      - 4.7.8.dev8
      - 4.7.8.dev9
```

For release versions, the application uses pre-built wheel files and pylock dependency specifications located in the distribution directory. The `${app.version}` variable is substituted with the actual version number in file paths.

#### Development Version

It can be very useful to add a development version for testing purposes. This version can be named anything (not just `devel`), and each person can have their own development version:

```yaml
  - version:
      - devel
```

The development version loads the application directly from the source code path and includes the `refresh: True` option to enable dynamic reloading during development.

### Commands

Each version defines two main commands:

- **dispatch**: Handles job dispatching operations
- **process**: Executes the actual processing tasks

Both commands use Python environments with specified dependency locks and can include environment variables and path modifications.

## Build Process

Application packages are created using the following uv commands:

1. **Lock dependencies**: `uv lock -U`
2. **Export pylock**: `uv export --format pylock.toml --no-export-project > pylock.toml`
3. **Build wheel**: `uv build`

The resulting wheel and pylock files are then copied into the slurmworker configuration directory and managed with git-lfs.

## Validation

The slurmworker repository contains a noxfile that allows running `nox` to validate all app YAML files for validity, which can be useful when updating configurations.

## Configuration Parameters

### Command Types

Commands can be of different types:

- `python_env`: Recommended for reproducible Python environments. This ensures that the app will be deployed exactly as developed without further modifications.
- `exec`: For simple shell scripts (refer to the app runner documentation for details)

### Parameters for python_env Commands

- `pylock`: Path to the Python dependency lock file
- `command`: Python module command to execute
- `local_extra_deps`: Additional local dependencies (wheels or source paths)

### Optional Parameters

- `refresh`: Enable dynamic reloading (development only)
- `env`: Environment variables to set (can include application-specific variables)
- `prepend_paths`: Additional paths to prepend to PATH environment variable

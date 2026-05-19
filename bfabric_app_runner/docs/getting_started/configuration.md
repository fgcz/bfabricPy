# Configuration

Applications for bfabric-app-runner are defined in an `app.yml` file. This file specifies the app runner version, application versions, and the commands to execute for each workflow stage.

## Basic Structure

An `app.yml` has two top-level sections:

```yaml
bfabric:
  app_runner: "0.2.1"

versions:
  - version: "1.0.0"
    commands:
      dispatch:
        type: python_env
        pylock: dist/v1.0.0/pylock.toml
        command: -m myapp.dispatch
        local_extra_deps:
          - dist/v1.0.0/myapp-1.0.0-py3-none-any.whl
      process:
        type: python_env
        pylock: dist/v1.0.0/pylock.toml
        command: -m myapp.process
        local_extra_deps:
          - dist/v1.0.0/myapp-1.0.0-py3-none-any.whl
```

`bfabric.app_runner`
: The app-runner version to pull from PyPI. This ensures reproducible execution regardless of which version is installed locally.

`versions`
: A list of application versions, each with its own commands for dispatch, process, and optionally collect.

## Command Types

Four command types are available: `python_env` (recommended), `shell`, `exec`, and `docker`. For a complete reference of all command types, their fields, and advanced features like multi-version templates and development versions, see the [Creating an App](../user_guides/creating_an_app.md) guide.

## Validation

Validate your `app.yml` against the expected schema:

```bash
bfabric-app-runner validate app-spec app.yml
```

## Next Steps

- [Creating an App](../user_guides/creating_an_app.md) -- Full reference for app.yml specification
- [Deploying Apps](../user_guides/deploying_apps.md) -- Building and deploying Python apps
- [Quick Start Tutorial](quick_start.md) -- Running a workunit step by step

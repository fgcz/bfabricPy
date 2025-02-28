# App Specification

## Overview

The bfabric-app-runner allows you to define and execute applications in various environments,
by configuring the application steps in a YAML configuration files, the so-called app specification.

## App Specification Structure

The specification can be provided in a YAML file with the following structure:

```yaml
versions:
  - version: "1.0.0"
    commands:
      dispatch: ...
      process: ...
      collect: ...  # Optional
```

## Commands

Each app defines these core commands:

- `dispatch`: Prepares input data. Called with: `$workunit_ref` `$work_dir`
- `process`: Executes main logic. Called with: `$chunk_dir`
- `collect`: (Optional) Organizes results. Called with: `$workunit_ref` `$chunk_dir`

Commands are discriminated by their `type` field.

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.app.commands_spec.CommandsSpec
```

### Shell Commands

```yaml
commands:
  dispatch:
    type: "shell"
    command: "python prepare_data.py"
```

The command string is split by spaces using `shlex.split()`.

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.app.commands_spec.CommandShell
```

### Docker Commands

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    command: "/app/run.sh"
    env:
      APP_VERSION: "${app.version}"
    mounts:
      read_only:
        - ["/data/reference", "/app/reference"]
      writeable:
        - ["/data/results", "/app/results"]
```

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.app.commands_spec.CommandDocker

.. autopydantic_model:: bfabric_app_runner.specs.app.commands_spec.MountOptions
```

## App Versions

The `AppVersionMultiTemplate` class defines app versions in two ways:

1. Single string: `version: "1.0.0"`
2. List of strings: `version: ["1.0.0", "1.0.1"]`

## Variables and Templating

Available variables for Mako templates:

- `${app.id}`: Application ID (integer)
- `${app.name}`: Application name (alphanumeric, underscores, hyphens)
- `${app.version}`: Version string

Example:

```yaml
image: "registry.example.com/${app.name}:${app.version}"
command: "/app/run.sh --app-id ${app.id}"
```

The `interpolate_config_strings` function processes all string values in the configuration after YAML loading.

## Loading and Using App Specifications

```python
from pathlib import Path
from bfabric_app_runner.specs.app_spec import AppSpec

# Load from YAML
app_spec = AppSpec.load_yaml(Path("./app_spec.yaml"), app_id="123", app_name="MyApp")

# Check version
if "1.0.0" in app_spec:
    app_version = app_spec["1.0.0"]
```

## Reference

```{eval-rst}
.. automodule:: bfabric_app_runner.specs.app_spec
    :members:
    :undoc-members:
    :show-inheritance:
```

```{eval-rst}
.. automodule:: bfabric_app_runner.specs.app.app_version
    :members:
    :undoc-members:
    :show-inheritance:
```

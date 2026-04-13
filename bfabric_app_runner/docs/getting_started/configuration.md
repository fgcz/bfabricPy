# Configuration

Applications for bfabric-app-runner are defined in an `app.yml` file. This file specifies the app runner version, application versions, and the commands to execute for each workflow stage.

______________________________________________________________________

## Basic Structure

An `app.yml` has two top-level sections:

```yaml
bfabric:
  app_runner: "0.2.1"

versions:
  - version: "1.0.0"
    commands:
      dispatch:
        type: shell
        command: "python -m myapp.dispatch"
      process:
        type: shell
        command: "python -m myapp.process"
```

### `bfabric` Section

```yaml
bfabric:
  app_runner: "0.2.1"
```

The `app_runner` field specifies which version of bfabric-app-runner to pull from PyPI. This ensures reproducible execution regardless of which version is installed locally.

### `versions` Section

Each entry in `versions` defines a named application version with its own commands:

```yaml
versions:
  - version: "1.0.0"
    commands:
      dispatch: ...
      process: ...
```

______________________________________________________________________

## Command Types

Each version defines `dispatch` and `process` commands (and optionally `collect`). Four command types are available:

### `python_env` (Recommended)

Creates a reproducible Python environment from a lock file. This is the recommended type for production use.

```yaml
commands:
  dispatch:
    type: python_env
    pylock: dist/v1.0.0/pylock.toml
    command: "python -m myapp.dispatch"
    local_extra_deps:
      - dist/v1.0.0/myapp-1.0.0-py3-none-any.whl
  process:
    type: python_env
    pylock: dist/v1.0.0/pylock.toml
    command: "python -m myapp.process"
    local_extra_deps:
      - dist/v1.0.0/myapp-1.0.0-py3-none-any.whl
```

Parameters:

- `pylock` -- Path to a pylock.toml dependency lock file
- `command` -- Python module or script to execute
- `local_extra_deps` -- Additional local wheels or source paths to install
- `python_version` -- Python version to use (optional)
- `env` -- Environment variables to set (optional)
- `prepend_paths` -- Paths to prepend to `PATH` (optional)
- `refresh` -- Enable dynamic reloading, for development only (optional)

### `shell`

Runs a simple shell command.

```yaml
commands:
  dispatch:
    type: shell
    command: "bash scripts/dispatch.sh"
```

### `exec`

Executes a command with environment and path customization.

```yaml
commands:
  process:
    type: exec
    command: "my-tool process"
    env:
      MY_VAR: "value"
    prepend_paths:
      - /opt/tools/bin
```

### `docker`

Runs a command inside a container.

```yaml
commands:
  process:
    type: docker
    image: myregistry/myapp:1.0
    command: "python -m myapp.process"
    engine: docker  # or "podman"
    mounts:
      share_bfabric_config: true
```

______________________________________________________________________

## Multiple Versions

You can define multiple versions in a single file. To avoid duplication when several versions share the same command structure, list them together:

```yaml
versions:
  - version:
      - "1.0.0"
      - "1.0.1"
      - "1.0.2"
    commands:
      dispatch:
        type: python_env
        pylock: dist/${app.version}/pylock.toml
        command: "python -m myapp.dispatch"
        local_extra_deps:
          - dist/${app.version}/myapp-${app.version}-py3-none-any.whl
      process:
        type: python_env
        pylock: dist/${app.version}/pylock.toml
        command: "python -m myapp.process"
        local_extra_deps:
          - dist/${app.version}/myapp-${app.version}-py3-none-any.whl
```

### Template Variables

When multiple versions share a definition, these template variables are available:

| Variable | Description |
|---|---|
| `${app.version}` | The current version string |
| `${app.id}` | The application ID |
| `${app.name}` | The application name |

These are interpolated using Mako templates at load time.

______________________________________________________________________

## Development Version

It is useful to add a development version for testing. This version loads the application directly from source code and enables dynamic reloading:

```yaml
versions:
  - version: devel
    commands:
      dispatch:
        type: python_env
        pylock: /home/user/myapp/pylock.toml
        command: "python -m myapp.dispatch"
        local_extra_deps:
          - /home/user/myapp
        refresh: true
      process:
        type: python_env
        pylock: /home/user/myapp/pylock.toml
        command: "python -m myapp.process"
        local_extra_deps:
          - /home/user/myapp
        refresh: true
```

The `refresh: true` flag causes the environment to be rebuilt each time, picking up source code changes. Each developer can have their own named development version.

To use the development version:

```bash
bfabric-app-runner prepare workunit /path/to/app.yml ./work 12345 --force-app-version devel
```

______________________________________________________________________

## Building Distribution Artifacts

For `python_env` commands, you need to produce a lock file and wheel. Use `uv` to build them:

```bash
# Lock dependencies
uv lock -U

# Export the lock file in pylock format
uv export --format pylock.toml --no-export-project > pylock.toml

# Build the wheel
uv build
```

Copy the resulting `.whl` and `pylock.toml` files into your distribution directory (e.g., `dist/v1.0.0/`).

______________________________________________________________________

## Validation

You can validate your `app.yml` against the expected schema:

```bash
bfabric-app-runner validate app-spec app.yml
```

Additional validation commands:

```bash
bfabric-app-runner validate app-spec-template template.yml
bfabric-app-runner validate inputs-spec inputs.yml
bfabric-app-runner validate outputs-spec outputs.yml
```

______________________________________________________________________

## See Also

- [Quick Start Tutorial](quick_start.md) -- Running a workunit step by step
- [Installation Guide](installation.md) -- Installation options

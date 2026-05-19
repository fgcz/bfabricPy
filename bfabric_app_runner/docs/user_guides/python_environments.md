# Python Environments

This guide explains how bfabric-app-runner manages Python virtual environments for the `python_env` command type.

## Overview

When a command uses `type: python_env`, the app runner automatically creates and manages a Python virtual environment with the specified dependencies. Two strategies are available:

- **Cached environments**: Persistent, reused across runs for the same dependency set.
- **Ephemeral environments**: Temporary, created fresh each run and cleaned up afterward.

## Cached Environments

By default, `python_env` commands use cached environments. The environment is identified by a hash computed from:

- Hostname
- Python version
- Absolute path to the pylock file
- Modification time of the pylock file
- Absolute paths of any local extra dependencies (if present)

If an environment with the same hash already exists and is fully provisioned, it is reused without reinstalling dependencies.

### Cache Location

Environments are stored under:

```
$XDG_CACHE_HOME/bfabric_app_runner/envs/<environment_hash>
```

If `XDG_CACHE_HOME` is not set, it defaults to `~/.cache/bfabric_app_runner/envs/`.

### Concurrency Safety

File locking (`<env_path>.lock`) prevents multiple processes from provisioning the same cached environment concurrently. A `.provisioned` marker file inside the environment directory indicates that provisioning completed successfully. Partially provisioned environments are not used.

## Ephemeral Environments

When `refresh: true` is set on a command, an ephemeral environment is created:

```
$XDG_CACHE_HOME/bfabric_app_runner/ephemeral/env_<random_suffix>
```

Ephemeral environments are always provisioned from scratch and automatically cleaned up after the command finishes. This is useful for:

- Development, where source code changes frequently.
- Testing, where a clean environment is needed each time.
- Debugging dependency issues.

## Provisioning Process

Whether cached or ephemeral, provisioning follows the same steps:

1. **Create virtual environment**: `uv venv` with the specified Python version.
2. **Install dependencies**: `uv pip install` from the pylock file.
3. **Install local extras**: If `local_extra_deps` are specified, install them with `--no-deps`.
4. **Mark as provisioned**: Create a `.provisioned` marker file.

:::{note}
Local extra dependencies (wheels or source paths) are installed with `--no-deps` because all dependencies are already covered by the pylock file. This ensures the wheel provides only the application code.
:::

## Environment Structure

A provisioned environment contains:

```
<env_path>/
  bin/
    python          # Python executable
    ...             # Other installed scripts
  lib/
    ...
  .provisioned      # Marker indicating successful provisioning
```

## Path Management

When a `python_env` command executes:

1. The environment's `bin/` directory is prepended to `PATH`.
2. Any `prepend_paths` specified in the command are also prepended.
3. Environment variables from the `env` field are set.
4. The command is executed using the environment's Python interpreter.

## Configuration Example

```yaml
commands:
  process:
    type: python_env
    pylock: /deploy/my_app/pylock.toml
    command: -m my_app.process
    python_version: "3.12"
    local_extra_deps:
      - /deploy/my_app/my_app-1.0.0-py3-none-any.whl
    env:
      DATA_PATH: /data
    prepend_paths:
      - /opt/tools/bin
    refresh: false   # Use cached environment (default)
```

## When to Use Refresh Mode

| Scenario | `refresh` | Rationale |
| ----------------------------- | --------- | ----------------------------------------- |
| Production deployment | `false` | Stable, cached environment for speed |
| Active development | `true` | Pick up source code changes immediately |
| Debugging dependency issues | `true` | Start fresh to isolate problems |
| CI/CD testing | `true` | Ensure clean environment each run |

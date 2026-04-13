# Creating an App

This guide explains how to define a bfabric-app-runner application using an `app.yml` specification file. This file is referenced as the "program" in a B-Fabric executable and is used by the app-runner submitter integration.

## App Specification

An `app.yml` file has two top-level sections:

```yaml
bfabric:
  app_runner: 0.2.1

versions:
  - version:
      - "1.0.0"
    commands:
      dispatch:
        type: shell
        command: echo "dispatching"
      process:
        type: shell
        command: echo "processing"
```

### The `bfabric` Section

`bfabric`
: Top-level configuration for B-Fabric integration.

`app_runner`
: The app-runner version to pull from PyPI (e.g. `"0.2.1"`).

`workflow_template_step_id`
: Optional. An integer identifying a workflow template step.

### The `versions` Section

Each entry defines one or more version identifiers and the commands to run for that version. The version is matched against the `application_version` key parameter in B-Fabric.

## Multi-Version Support

To avoid configuration duplication, you can list multiple version identifiers that share the same command definitions:

```yaml
versions:
  - version:
      - 4.7.8.dev3
      - 4.7.8.dev4
      - 4.7.8.dev8
    commands:
      dispatch:
        type: python_env
        pylock: /path/to/dist/${app.version}/pylock.toml
        local_extra_deps:
          - /path/to/dist/${app.version}/my_app-${app.version}-py3-none-any.whl
        command: -m my_app.dispatch
      process:
        type: python_env
        pylock: /path/to/dist/${app.version}/pylock.toml
        local_extra_deps:
          - /path/to/dist/${app.version}/my_app-${app.version}-py3-none-any.whl
        command: -m my_app.process
```

### Template Variables

When multiple versions share a definition, the following template variables are available for path interpolation:

`${app.version}`
: The actual version string being resolved (e.g. `"4.7.8.dev3"`).

`${app.id}`
: The B-Fabric application ID (provided at resolution time).

`${app.name}`
: The B-Fabric application name (provided at resolution time).

These variables use Mako template interpolation and are resolved when the app spec is loaded.

## Command Types

Each version defines commands for different execution phases. Four command types are available.

### shell

Runs a command through the system shell.

```yaml
type: shell
command: "echo hello"
```

Fields:
- `command` (str, required): The shell command to execute.

### exec

Executes a command directly (no shell interpretation).

```yaml
type: exec
command: "/path/to/my_script.sh"
env:
  MY_VAR: "value"
prepend_paths:
  - /opt/tools/bin
```

Fields:
- `command` (str, required): The command to execute.
- `env` (dict, optional): Environment variables to set.
- `prepend_paths` (list of paths, optional): Directories to prepend to `PATH`.

### docker

Runs a command inside a Docker or Podman container.

```yaml
type: docker
image: "my-registry/my-app:latest"
command: "python -m my_app.run"
engine: docker
env:
  DATA_PATH: /data
mounts:
  work_dir_target: /work
  share_bfabric_config: true
  read_only:
    - [/host/ref, /container/ref]
  writeable:
    - [/host/out, /container/out]
```

Fields:
- `image` (str, required): The container image.
- `command` (str, required): The command to run inside the container.
- `entrypoint` (str, optional): Override the container entrypoint.
- `engine` (str, optional): `"docker"` or `"podman"`. Defaults to `"docker"`.
- `env` (dict, optional): Environment variables.
- `mac_address` (str, optional): MAC address for the container.
- `hostname` (str, optional): Hostname for the container.
- `custom_args` (list, optional): Additional arguments passed to the container engine.
- `mounts` (MountOptions, optional): Mount configuration.

MountOptions fields:
- `work_dir_target` (str): Mount point for the working directory inside the container.
- `share_bfabric_config` (bool): Whether to mount the B-Fabric config into the container.
- `read_only` (list of [host, container] pairs): Read-only bind mounts.
- `writeable` (list of [host, container] pairs): Writeable bind mounts.

### python_env

Creates a managed Python virtual environment and runs a command in it. This is the recommended type for reproducible deployments.

```yaml
type: python_env
pylock: /path/to/pylock.toml
command: -m my_app.main
local_extra_deps:
  - /path/to/my_app-1.0.0-py3-none-any.whl
env:
  MY_SETTING: "value"
prepend_paths:
  - /opt/tools/bin
```

Fields:
- `pylock` (path, required): Path to the pylock.toml dependency lock file.
- `command` (str, required): The Python command to execute (typically `-m module.name`).
- `python_version` (str, optional): Python version to use.
- `local_extra_deps` (list of paths, optional): Local wheel files or source paths to install with `--no-deps`.
- `env` (dict, optional): Environment variables.
- `prepend_paths` (list of paths, optional): Directories to prepend to `PATH`.
- `refresh` (bool, optional): Use an ephemeral environment instead of cached. Useful for development.

See [Python Environments](python_environments.md) for details on caching and provisioning.

## Commands Spec

Each version defines a `commands` block with up to three phases:

`dispatch`
: Called with `$workunit_ref $work_dir`. Creates chunk directories and prepares input specifications.

`process`
: Called with `$chunk_dir`. Executes the actual computation for each chunk.

`collect`
: Optional. Called with `$workunit_ref $chunk_dir`. Runs after processing to aggregate results or perform cleanup.

```yaml
commands:
  dispatch:
    type: python_env
    pylock: /path/to/pylock.toml
    command: -m my_app.dispatch
  process:
    type: python_env
    pylock: /path/to/pylock.toml
    command: -m my_app.process
  collect:
    type: shell
    command: "echo 'collection complete'"
```

## Development Version

For development and testing, add a version entry that loads code directly from source with the `refresh` flag:

```yaml
  - version:
      - devel
    commands:
      dispatch:
        type: python_env
        pylock: /home/user/my_app/pylock.toml
        local_extra_deps:
          - /home/user/my_app/src
        command: -m my_app.dispatch
        refresh: true
      process:
        type: python_env
        pylock: /home/user/my_app/pylock.toml
        local_extra_deps:
          - /home/user/my_app/src
        command: -m my_app.process
        refresh: true
```

Setting `refresh: true` creates an ephemeral environment on each run, so code changes are picked up immediately without rebuilding.

:::{tip}
Each developer can add their own development version (e.g. `devel-alice`, `devel-bob`) to test independently.
:::

## Validation

Validate your app specification before deployment:

```bash
# Validate basic structure
bfabric-app-runner validate app-spec app.yml

# Validate with template variable context
bfabric-app-runner validate app-spec app.yml --app-id 123 --app-name my_app

# Validate an unresolved template file
bfabric-app-runner validate app-spec-template app.yml
```

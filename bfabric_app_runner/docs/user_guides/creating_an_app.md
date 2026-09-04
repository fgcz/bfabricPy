# Creating an App

This guide explains how to define a bfabric-app-runner application using an `app.yml` specification file. This file is referenced as the "program" in a B-Fabric executable and is used by the app-runner submitter integration.

## App Specification

An `app.yml` file has two top-level sections:

```yaml
bfabric:
  app_runner: 0.8.0

versions:
  - version:
      - "1.0.0"
    commands:
      dispatch:
        type: exec
        command: echo "dispatching"
      process:
        type: exec
        command: echo "processing"
```

### The `bfabric` Section

`bfabric`
: Top-level configuration for B-Fabric integration.

`app_runner`
: The app-runner version to pull from PyPI (e.g. `"0.8.0"`).

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
        pylock: dist/${app.version}/pylock.toml
        local_extra_deps:
          - dist/${app.version}/my_app-${app.version}-py3-none-any.whl
        command: -m my_app.dispatch
      process:
        type: python_env
        pylock: dist/${app.version}/pylock.toml
        local_extra_deps:
          - dist/${app.version}/my_app-${app.version}-py3-none-any.whl
        command: -m my_app.process
```

Path fields are resolved relative to the directory containing the `app.yml`; see
[Paths](../specs/app_specification.md#paths).

### Template Variables

When multiple versions share a definition, the following template variables are available for path interpolation:

`${app.version}`
: The actual version string being resolved (e.g. `"4.7.8.dev3"`).

`${app.id}`
: The B-Fabric application ID (provided at resolution time).

`${app.name}`
: The B-Fabric application name (provided at resolution time).

`${app.dir}`
: The directory containing the `app.yml`. Use it for paths that are not path fields, i.e. inside a
  `command` string or an `env` value, where they cannot be resolved automatically.

These variables use Mako template interpolation and are resolved when the app spec is loaded.

## Command Types

Each version defines commands for different execution phases. Four command types are available; the fields
of each are documented in the [App specification](../specs/app_specification.md).

### shell (deprecated)

:::{note}
**Deprecated** -- use `exec` instead. `shell` splits the command string on plain spaces (no quoting or shell
features), which `exec` does more robustly via `shlex.split`.
:::

```yaml
type: shell
command: "echo hello"
```

### exec

Executes a command directly (no shell interpretation).

```yaml
type: exec
command: "${app.dir}/my_script.sh"
env:
  MY_VAR: "value"
prepend_paths:
  - /opt/tools/bin
```

A script that lives next to the `app.yml` is best referenced with `${app.dir}`: paths inside a
command string are passed through as written, so a relative one would be interpreted against the
working directory of the run, not the app.

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

### python_env

Creates a managed Python virtual environment and runs a command in it. This is the recommended type for reproducible deployments.

```yaml
type: python_env
pylock: dist/pylock.toml
command: -m my_app.main
local_extra_deps:
  - dist/my_app-1.0.0-py3-none-any.whl
env:
  MY_SETTING: "value"
prepend_paths:
  - /opt/tools/bin
```

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
    pylock: dist/pylock.toml
    command: -m my_app.dispatch
  process:
    type: python_env
    pylock: dist/pylock.toml
    command: -m my_app.process
  collect:
    type: exec
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
An app whose code lives next to the `app.yml` (scripts referenced via `${app.dir}`, or a wheel under
`dist/`) usually needs no such entry at all: the same definition already works from every checkout.
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

# App Specification

This guide covers creating an `app_spec.yml` file, which defines your bioinformatics application's structure, versions, and execution commands.

## Overview

The app specification (`app_spec.yml`) is a YAML file that:

- Defines your application's metadata
- Specifies available versions
- Configures execution commands for each phase (dispatch, process, collect)
- Supports Mako templating for dynamic configuration
- Centralizes configuration across multiple app versions

## App Specification Structure

```yaml
bfabric:
  app_runner: "1.0.0"  # bfabric-app-runner version requirement
  workflow_template_step_id: 100  # Optional: workflow step ID

versions:
  - version: "1.0.0"
    commands:
      dispatch: ...
      process: ...
      collect: ...  # Optional
```

### bfabric Section

The `bfabric` section contains B-Fabric integration settings:

| Field | Type | Required | Description |
| ------------------------ | --------------- | -------- | ------------------------------------------------------------ |
| **app_runner** | string | Yes | bfabric-app-runner version requirement (e.g., `1.0.0` or git ref) |
| **workflow_template_step_id** | integer | No | Workflow step ID for B-Fabric workflow integration |

### App Runner Version Specification

The `app_runner` field supports two formats:

**PyPI Version:**

```yaml
bfabric:
  app_runner: "1.0.0"
```

**Git Reference:**

```yaml
bfabric:
  app_runner: "git+https://github.com/fgcz/bfabricPy@main#subdirectory=bfabric_app_runner"
```

This is useful for:

- Development versions
- Specific commits
- Custom branches

## Versions

Each app can have multiple versions. Versions are processed sequentially when resolving the specification:

### Single Version

```yaml
versions:
  - version: "1.0.0"
    commands: ...
```

### Multiple Versions

```yaml
versions:
  - version: "1.0.0"
    commands: ...
  - version: "1.1.0"
    commands: ...
  - version: "2.0.0"
    commands: ...
```

```{note}
Version strings must be unique within an app specification.
```

### Version Expansion

You can specify multiple versions in a single entry:

```yaml
versions:
  - version: ["1.0.0", "1.0.1", "1.0.2"]
    commands: ...
```

This creates versions `1.0.0`, `1.0.1`, and `1.0.2` with identical commands.

## Commands

Each version defines commands for three workflow phases:

### Command Phases

| Phase | Purpose | Context |
| ---------- | -------------------------------------------- | -------------------------------- |
| **dispatch** | Prepare workflow parameters and context | `$workunit_ref` `$work_dir` |
| **process** | Execute the main application logic | `$chunk_dir` |
| **collect** | Post-processing and cleanup (optional) | `$workunit_ref` `$chunk_dir` |

### Command Types

Commands are discriminated by their `type` field:

#### 1. Shell Commands (Deprecated)

```yaml
commands:
  process:
    type: "shell"
    command: "python script.py"
```

```{warning}
The `shell` type is deprecated. Use `exec` instead.
```

#### 2. Exec Commands

Execute a command using `shlex.split()`:

```yaml
commands:
  process:
    type: "exec"
    command: "python3 script.py --input data.csv"
    env:
      PYTHONPATH: "/usr/local/lib/python3.11"
    prepend_paths:
      - "/usr/local/bin"
```

**Options:**

| Field | Type | Description |
| ----------------- | ------------ | --------------------------------------------------- |
| **command** | string | Command to execute (split by spaces) |
| **env** | dict | Environment variables to set before execution |
| **prepend_paths** | list[Path] | Paths to prepend to PATH variable |

#### 3. Docker Commands

Run applications in Docker containers:

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    command: "/app/run.py"
    entrypoint: "/usr/bin/python3"
    engine: "docker"
    env:
      APP_VERSION: "1.0.0"
    mounts:
      read_only:
        - ["./inputs", "/app/data"]
      writeable:
        - ["./outputs", "/app/output"]
    hostname: "myapp-host"
    custom_args:
      - "--network=host"
```

**Options:**

| Field | Type | Description |
| -------------------- | ------------------------- | ------------------------------------------------------------ |
| **image** | string | Docker image to run |
| **command** | string | Command to execute in container |
| **entrypoint** | string | Override image's entrypoint (optional) |
| **engine** | "docker" | "podman" | Container engine to use |
| **env** | dict | Environment variables for container |
| **mounts** | MountOptions | Volume mount configuration |
| **hostname** | string | Container hostname |
| **mac_address** | string | Container MAC address (optional) |
| **custom_args** | list | Custom CLI arguments for container engine |

**Mount Options:**

| Field | Type | Description |
| -------------------- | --------------------------- | -------------------------------------------------- |
| **work_dir_target** | Path | Target for work directory mount (optional) |
| **read_only** | list\[tuple[Path, Path]\] | Read-only volume mounts (host:container) |
| **writeable** | list\[tuple[Path, Path]\] | Writable volume mounts (host:container) |
| **share_bfabric_config** | boolean | Share B-Fabric config with container (default: true) |

#### 4. Python Environment Commands

Run Python applications in virtual environments:

```yaml
commands:
  process:
    type: "python_env"
    pylock: "./requirements.lock"
    command: "python main.py"
    python_version: "3.11"
    local_extra_deps:
      - "./my_lib.whl"
    env:
      MY_VAR: "value"
    prepend_paths:
      - "/opt/custom/bin"
```

**Options:**

| Field | Type | Description |
| ------------------- | -------------- | --------------------------------------------------------- |
| **pylock** | Path | Path to `.lock` file specifying dependencies (uv or pip) |
| **command** | string | Command to execute (split by spaces) |
| **python_version** | string | Python version to use (optional) |
| **local_extra_deps** | list[Path] | Additional local dependencies (wheels, sdist, package dirs) |
| **env** | dict | Environment variables to set |
| **prepend_paths** | list[Path] | Paths to prepend to PATH |

## Complete Example

Here's a complete app specification for a data processing pipeline:

```yaml
# app_spec.yml

bfabric:
  app_runner: "1.0.0"
  workflow_template_step_id: 100

versions:
  - version: "1.0.0"
    commands:
      # Phase 1: Prepare workflow
      dispatch:
        type: "exec"
        command: "python generate_workflow.py"
        env:
          WORKFLOW_VERSION: "1.0.0"

      # Phase 2: Process data
      process:
        type: "docker"
        image: "myprocessor:1.0.0"
        command: "/app/process_data.py"
        env:
          APP_VERSION: "${app.version}"
          APP_NAME: "${app.name}"
        mounts:
          read_only:
            - ["./inputs", "/app/data"]
          writeable:
            - ["./outputs", "/app/results"]

      # Phase 3: Post-processing
      collect:
        type: "exec"
        command: "python finalize_results.py"
```

## Variables and Templating

App specifications support Mako templating with the following variables:

| Variable | Description | Example |
| ------------------ | --------------------------------------------- | ------------------------------------ |
| **${app.id}** | Application ID (integer) | `123` |
| **${app.name}** | Application name (alphanumeric + underscores/hyphens) | `my_processor_app` |
| **${app.version}** | Version string | `1.0.0` |

### Templating Examples

```yaml
# Use app version in Docker image
process:
  type: "docker"
  image: "registry.example.com/${app.name}:${app.version}"

# Use app ID and name in environment variables
process:
  type: "exec"
  env:
    APP_ID: "${app.id}"
    APP_NAME: "${app.name}"

# Use app version in command
process:
  type: "exec"
  command: "python script.py --version ${app.version}"
```

## Validating App Specifications

Validate your app specification before using it:

```bash
# Validate without app_id/app_name
bfabric-app-runner validate app-spec-template app_spec.yml

# Validate with specific app_id/app_name
bfabric-app-runner validate app-spec app_spec.yml --app-id 123 --app-name "MyApp"
```

Expected output:

```
BfabricAppSpec(
  app_runner='1.0.0',
  workflow_template_step_id=100,
  versions=[
    AppVersion(
      version='1.0.0',
      commands=CommandsSpec(dispatch=..., process=...)
    )
  ]
)
```

## Next Steps

- **[Defining Commands](defining_commands.md)** - Detailed command configuration
- **[Versioning Guide](versioning.md)** - Managing multiple app versions
- **[Input Specification](../working_with_inputs/input_specification.md)** - Defining input data
- **[Output Specification](../working_with_outputs/output_specification.md)** - Defining output data

## Related Documentation

- [Quick Start Tutorial](../../getting_started/quick_start.md) - Hands-on introduction
- [API Reference](../../api_reference/app_specification.md) - Complete Pydantic model documentation
- [Docker Environment](../execution/docker_environment.md)\*\* - Container configuration

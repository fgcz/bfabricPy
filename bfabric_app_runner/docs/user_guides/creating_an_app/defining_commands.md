# Defining Commands

This guide covers configuring execution commands in your `app_spec.yml`, including the three workflow phases: dispatch, process, and collect.

## Overview

Each app version can define commands for three workflow phases:

| Phase | Purpose | Called With | Typical Use |
| ---------- | ---------------------------------------------- | ----------------------------- | ------------------------------------ |
| **dispatch** | Prepare workflow parameters and context | `$workunit_ref` `$work_dir` | Generate config files, setup environment |
| **process** | Execute the main application logic | `$chunk_dir` | Run data processing, analysis, computation |
| **collect** | Post-processing and cleanup (optional) | `$workunit_ref` `$chunk_dir` | Finalize results, cleanup temp files |

## Command Context Variables

Commands receive different variables depending on the phase:

### Dispatch Context

```bash
$workunit_ref    # Path to workunit definition (YAML) or workunit ID
$work_dir        # Path to workunit directory
```

### Process Context

```bash
$chunk_dir       # Path to chunk directory (subset of work_dir)
```

### Collect Context

```bash
$workunit_ref    # Path to workunit definition (YAML) or workunit ID
$chunk_dir       # Path to chunk directory (subset of work_dir)
```

## Command Types

### 1. Exec Commands

Execute a command using shell-like execution (split by spaces):

```yaml
commands:
  process:
    type: "exec"
    command: "python3 script.py --input data.csv --output results.txt"
```

**Command Splitting:**

The command string is split using `shlex.split()`, which properly handles quoted arguments:

```yaml
# Correct: Arguments are properly quoted
command: 'python3 script.py --name "My Data" --verbose'

# Splits to: ["python3", "script.py", "--name", "My Data", "--verbose"]
```

**Environment Variables:**

```yaml
commands:
  process:
    type: "exec"
    command: "python3 script.py"
    env:
      PYTHONPATH: "/usr/local/lib/python3.11"
      DATA_DIR: "/app/data"
      LOG_LEVEL: "INFO"
```

**PATH Prepending:**

```yaml
commands:
  process:
    type: "exec"
    command: "my_tool --input data.csv"
    prepend_paths:
      - "/opt/mytool/bin"
      - "/usr/local/bin"
```

### 2. Docker Commands

Run applications in Docker containers with full isolation:

```yaml
commands:
  process:
    type: "docker"
    image: "mybioapp:1.0.0"
    command: "/app/run.py --input /app/data/input.csv"
```

**Image Options:**

```yaml
commands:
  process:
    type: "docker"
    image: "myregistry.com/bioapp:1.2.3"  # From custom registry
    engine: "podman"                    # Use Podman instead of Docker
    entrypoint: "/usr/bin/python3"          # Override default entrypoint
```

**Environment Variables:**

```yaml
commands:
  process:
    type: "docker"
    image: "mybioapp:1.0.0"
    command: "/app/run.py"
    env:
      APP_VERSION: "${app.version}"
      DATA_PATH: "/app/data"
      NUM_WORKERS: "4"
```

**Volume Mounts:**

```yaml
commands:
  process:
    type: "docker"
    image: "mybioapp:1.0.0"
    mounts:
      # Read-only mounts (host:container)
      read_only:
        - ["./inputs", "/app/data"]
        - ["/opt/reference", "/app/reference"]
      # Writable mounts (host:container)
      writeable:
        - ["./outputs", "/app/results"]
      # Work directory target (optional)
      work_dir_target: "/app"
      # Share B-Fabric config with container
      share_bfabric_config: true
```

**Container Identity:**

```yaml
commands:
  process:
    type: "docker"
    image: "mybioapp:1.0.0"
    hostname: "mybioapp-host"     # Container hostname
    mac_address: "02:42:ac:11:00:02"  # Specific MAC address
```

**Custom Arguments:**

```yaml
commands:
  process:
    type: "docker"
    image: "mybioapp:1.0.0"
    custom_args:
      - "--network=host"           # Use host network
      - "--memory=8g"             # Limit memory
      - "--cpus=4"               # Limit CPUs
```

### 3. Python Environment Commands

Run Python applications with uv-managed virtual environments:

```yaml
commands:
  process:
    type: "python_env"
    pylock: "./requirements.lock"
    command: "python main.py --input data.csv"
```

**Python Lock File:**

The `pylock` file specifies dependencies using uv or pip lock format:

```bash
# requirements.lock
app = "==1.0.0"
numpy = "==1.26.0"
pandas = "==2.1.0"
```

**Python Version:**

```yaml
commands:
  process:
    type: "python_env"
    pylock: "./requirements.lock"
    python_version: "3.11"  # Use specific Python version
    command: "python main.py"
```

**Local Dependencies:**

```yaml
commands:
  process:
    type: "python_env"
    pylock: "./requirements.lock"
    local_extra_deps:
      - "./my_lib.whl"              # Local wheel
      - "./custom_package/"           # Local package directory
      - "./my_extension.tar.gz"      # Source distribution
    command: "python main.py"
```

```{note}
Local dependencies are installed with `uv pip install --no-deps` without dependency resolution. Ensure all dependencies are satisfied by the lock file.
```

**Environment Variables and PATH:**

```yaml
commands:
  process:
    type: "python_env"
    pylock: "./requirements.lock"
    command: "python main.py"
    env:
      PYTHONPATH: "/custom/lib"
      MY_CONFIG: "/app/config.yaml"
    prepend_paths:
      - "/opt/custom-tools/bin"
```

## Example: Complete Command Configuration

Here's a complete example with all three phases:

```yaml
versions:
  - version: "1.0.0"
    commands:
      # Phase 1: Prepare workflow
      dispatch:
        type: "exec"
        command: "python generate_config.py --config workflow_params.json"
        env:
          WORKFLOW_VERSION: "1.0.0"
        prepend_paths:
          - "./scripts"

      # Phase 2: Process data (Docker)
      process:
        type: "docker"
        image: "processor:1.0.0"
        command: "/app/process.py --config /app/config/workflow_params.json"
        env:
          APP_VERSION: "${app.version}"
          NUM_WORKERS: "4"
        mounts:
          read_only:
            - ["./inputs", "/app/data"]
            - ["/opt/reference_genome", "/app/reference"]
          writeable:
            - ["./outputs", "/app/results"]
          share_bfabric_config: true

      # Phase 3: Finalize results
      collect:
        type: "exec"
        command: "python finalize.py --results-dir ./outputs"
```

## Best Practices

### Use Exec Commands for Simple Scripts

For simple Python/shell scripts, use `exec` commands:

```yaml
# Good for simple scripts
process:
  type: "exec"
  command: "python script.py"
```

### Use Docker for Complex Applications

For applications with complex dependencies, use Docker:

```yaml
process:
  type: "docker"
  image: "myapp:1.0.0"
  command: "/app/run.py"
```

### Use Python Environment for Python Apps

For Python applications, use `python_env` commands:

```yaml
process:
  type: "python_env"
  pylock: "./requirements.lock"
  command: "python main.py"
```

### Use Environment Variables for Configuration

Avoid hardcoding configuration:

```yaml
# Bad: Hardcoded paths
process:
  type: "exec"
  command: "python /opt/app/script.py"

# Good: Use environment variables
process:
  type: "exec"
  command: "python ${APP_SCRIPT}"
  env:
    APP_SCRIPT: "/opt/app/script.py"
```

### Use Templating for Dynamic Values

Leverage `${app.id}`, `${app.name}`, `${app.version}`:

```yaml
process:
  type: "docker"
  image: "registry.com/${app.name}:${app.version}"
  env:
    APP_ID: "${app.id}"
    APP_NAME: "${app.name}"
```

### Define Collect Phase for Cleanup

Always include a collect phase to clean up temporary files:

```yaml
collect:
  type: "exec"
  command: "python cleanup.py --remove-temp"
```

## Common Patterns

### Running Multiple Commands in a Phase

Use a shell script or chained commands:

```yaml
process:
  type: "exec"
  command: "python prepare_data.py && python process.py && python finalize.py"
```

### Conditional Execution

Use environment variables to control execution:

```yaml
process:
  type: "exec"
  command: "python ${COMMAND}"
  env:
    COMMAND: "${RUN_FAST:-process_fast.py}"
```

### Debugging Commands

Add debug flags during development:

```yaml
process:
  type: "exec"
  command: "python script.py --debug --verbose"
  env:
    DEBUG: "true"
    LOG_LEVEL: "DEBUG"
```

## Next Steps

- **[App Specification](app_specification.md)** - Complete app_spec.yml structure
- **[Versioning Guide](versioning.md)** - Managing multiple app versions
- **[Docker Environment](../execution/docker_environment.md)** - Advanced Docker configuration
- **[Python Environment](../execution/python_environment.md)** - Advanced Python environment configuration

## Related Documentation

- [Quick Start Tutorial](../../getting_started/quick_start.md) - Hands-on introduction
- [Input Specification](../working_with_inputs/input_specification.md) - Defining input data
- [Output Specification](../working_with_outputs/output_specification.md) - Defining output data
- [API Reference](../../api_reference/app_specification.md) - Complete command type documentation

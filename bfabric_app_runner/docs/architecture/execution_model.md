# Execution Model

This document explains the different execution models supported by bfabric-app-runner.

## Overview

bfabric-app-runner supports multiple execution models, each optimized for different use cases:

| Model | Description | When to Use | Isolation Level |
| ---------- | -------------------------------------------- | ------------------------------------- | --------------- |
| **Direct** | Execute commands on host system | Simple scripts, quick jobs | None |
| **Docker** | Run applications in containers | Isolated, reproducible environments | Full |
| **Python Env**| Run in uv-managed Python environments | Python applications with dependencies | Process-level |

## Direct Execution

### How It Works

Commands execute directly on the host system using `shlex.split()`:

```yaml
commands:
  process:
    type: "exec"
    command: "python3 process.py --input data.csv"
```

**Execution Flow:**

```
Host Shell
    ↓
shlex.split() → subprocess.run()
    ↓
Python process.py
```

**Characteristics:**

- Simple and fast (no container overhead)
- Uses host dependencies and environment
- Direct file system access
- No isolation between workunits
- Good for development and testing

**When to Use:**

- Quick scripts and tools
- Development work
- Testing locally
- Jobs with minimal dependencies
- When full isolation is't required

**Limitations:**

- Dependency conflicts with host system
- Environment pollution
- Reproducibility issues across different machines

## Docker Execution

### How It Works

Commands execute in Docker containers with full isolation:

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    command: "/app/process.py"
    mounts:
      read_only:
        - ["./inputs", "/app/data"]
      writeable:
        - ["./outputs", "/app/results"]
```

**Execution Flow:**

```
Host System
    ↓
Docker Engine
    ↓
Container Isolation
    ↓
Application Logic
    ↓
Generate Outputs
```

**Characteristics:**

- Full isolation from host system
- Reproducible environments (same image = same behavior)
- Easy deployment across different machines
- Can limit resources (CPU, memory, disk)
- Self-contained dependencies

**When to Use:**

- Production applications
- Complex software stacks
- Jobs requiring specific environments
- Multi-user deployments
- When reproducibility is critical

**Benefits:**

- Consistent behavior across environments
- No "works on my machine" issues
- Easy to test and debug locally
- Can run anywhere Docker is available

## Python Virtual Environment

### How It Works

Commands execute in uv-managed Python virtual environments:

```yaml
commands:
  process:
    type: "python_env"
    pylock: "./requirements.lock"
    command: "python process.py"
    local_extra_deps:
      - "./my_lib.whl"
```

**Execution Flow:**

```
Host System
    ↓
uv (package manager)
    ↓
Virtual Environment (isolated)
    ↓
Python Application
```

**Characteristics:**

- Isolated Python dependencies
- Reproducible with lock files
- Can specify Python version
- Process-level isolation (not container-level)

**When to Use:**

- Python applications
- When specific Python version is required
- When managing complex dependencies
- For applications requiring isolated Python environments

**Benefits:**

- Exact dependency matching (with lock files)
- No system Python pollution
- Easy to reproduce exact environment

## Execution Model Comparison

| Aspect | Direct | Docker | Python Env |
| -------------------- | -------------------------- | ----------------------------------------- | --------------------------------- |
| **Startup Time** | Fast (no container boot) | Slower (container initialization) | Fast |
| **Resource Usage** | Uses host resources | Additional overhead for container | Moderate (Python runtime) |
| **Isolation** | None | Full container isolation | Process-level (no host access) |
| **Reproducibility** | Depends on host setup | Excellent (containerized) | Excellent (lock files) |
| **Portability** | Machine-dependent | High (Docker available anywhere) | Low (needs Python installed) |
| **Dependencies** | System-wide | Containerized | Environment-specific |
| **Debugging** | Easy (attach to process) | Moderate (need to enter container) | Easy (no container to enter) |

## Choosing an Execution Model

### Decision Tree

```
Start
  │
  ├─ Need Python isolation?
  │   ├─ Yes → Python Environment
  │   └─ No → Continue
  │
  ├─ Need full container isolation?
  │   ├─ Yes → Docker
  │   └─ No → Continue
  │
  ├─ Are dependencies complex?
  │   ├─ Yes → Docker (for simplicity)
  │   └─ No → Continue
  │
  └─ Is this for production?
      ├─ Yes → Docker (reproducibility)
      └─ No → Direct (faster execution)
```

### Recommendations

| Scenario | Recommended Model |
| ------------------------------------------ | ------------------------------------ |
| **Simple Python script** | Python Environment (no extra deps) or Direct |
| **Python app with complex dependencies** | Python Environment (with lock file) |
| **Bioinformatics tool in Docker** | Docker (existing Docker image) |
| **Multi-language stack (Python + R + other)** | Docker (containerize everything) |
| **Production data processing** | Docker (reproducible + isolated) |
| **Quick ad-hoc analysis** | Direct (fastest, no setup needed) |
| **Development work** | Direct or Python Environment (easy debugging) |
| **Testing locally** | Python Environment or Docker (isolated) |
| **SLURM job** | Docker or Direct (depends on cluster) |

## Advanced: Mixed Execution

Different phases can use different execution models:

```yaml
versions:
  - version: "1.0.0"
    commands:
      # Prepare on host
      dispatch:
        type: "exec"
        command: "python generate_config.py"

      # Process in Docker
      process:
        type: "docker"
        image: "myapp:1.0.0"
        command: "/app/process.py"

      # Finalize on host
      collect:
        type: "exec"
        command: "python finalize.py"
```

**Use Case:**

- Setup/teardown on host (faster)
- Main computation in container (isolated)
- Finalization on host (access to outputs)

## Resource Management

### Docker Resource Limits

Control container resource usage:

```yaml
commands:
  process:
    type: "docker"
    custom_args:
      - "--memory=8g"      # 8GB RAM limit
      - "--cpus=4"         # 4 CPU cores limit
      - "--disk=20g"       # 20GB disk limit
      - "--gpus=all"       # Use all available GPUs
```

### Direct Resource Usage

Direct execution uses host resources directly:

```bash
# Limit process CPU cores
taskset -c 0-3 python process.py

# Nice process (lower priority)
nice -n 19 python process.py
```

### Python Environment Resources

uv manages virtual environment resources:

```bash
# No explicit limits (uses system resources)
uv run --python 3.11 process.py

# Can specify memory with Python options
uv run --python 3.11 -Xmx4g process.py
```

## Related Documentation

- **[Docker Environment](../execution/docker_environment.md)** - Docker configuration details
- **[Python Environment](../execution/python_environment.md)** - Python environment details
- **[Defining Commands](../creating_an_app/defining_commands.md)** - Command configuration
- **[Complete Workflow](../workflows/complete_workflow.md)** - End-to-end execution

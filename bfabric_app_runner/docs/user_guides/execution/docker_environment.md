# Docker Environment

This guide covers using Docker containers for running bfabric-app-runner applications.

## Overview

Docker provides isolated, reproducible execution environments with:

- **Container isolation** - No dependency conflicts with host
- **Reproducibility** - Same image = same behavior
- **Portability** - Run anywhere Docker is available
- **Resource control** - Limit CPU, memory, and disk usage

## Docker Command Configuration

### Basic Docker Command

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    command: "/app/run.py"
```

### Container Image

```yaml
commands:
  process:
    type: "docker"
    image: "registry.example.com/bioapp:1.2.3"  # Custom registry
    # or
    image: "myapp:1.0.0"  # Docker Hub
    # or
    image: "docker.io/library/python:3.11-slim"  # Official image
```

### Container Command

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    command: "/usr/bin/python3 /app/run.py --input data.csv"
```

### Entrypoint Override

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    entrypoint: "/usr/bin/python3"  # Override image default
    command: "/app/run.py"
```

### Environment Variables

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    command: "/app/run.py"
    env:
      APP_VERSION: "1.0.0"
      DATABASE_HOST: "postgres.example.com"
      DATABASE_PORT: "5432"
      NUM_WORKERS: "4"
```

### B-Fabric Config Sharing

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    command: "/app/run.py"
    mounts:
      share_bfabric_config: true  # Share ~/.bfabricpy.yml with container (default)
```

```{note}
Setting `share_bfabric_config: true` allows the container to access B-Fabric credentials for direct API calls.
```

## Volume Mounts

Mounts map host directories into the container:

### Read-Only Mounts

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    command: "/app/process.py"
    mounts:
      read_only:
        - ["./inputs", "/app/data"]                    # Input data
        - ["/opt/reference_genome", "/app/reference"]  # Reference files
```

### Writable Mounts

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    command: "/app/process.py"
    mounts:
      writeable:
        - ["./outputs", "/app/results"]  # Output directory
```

### Multiple Mounts

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    command: "/app/process.py"
    mounts:
      read_only:
        - ["./inputs", "/app/data"]
        - ["/opt/reference", "/app/reference"]
      writeable:
        - ["./outputs", "/app/results"]
        - ["./temp", "/app/tmp"]
```

### Work Directory Target

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    command: "/app/process.py"
    mounts:
      work_dir_target: "/app"  # Mount work directory as /app
```

## Container Engine

bfabric-app-runner supports both Docker and Podman:

### Docker (Default)

```yaml
commands:
  process:
    type: "docker"
    engine: "docker"  # Default
    image: "myapp:1.0.0"
```

### Podman

```yaml
commands:
  process:
    type: "docker"
    engine: "podman"  # Use Podman instead of Docker
    image: "myapp:1.0.0"
```

```{note}
Podman is a drop-in Docker alternative with better security and rootless containers.
```

## Container Identity

### Hostname

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    hostname: "mybioapp-host"
    command: "/app/run.py"
```

### MAC Address

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    mac_address: "02:42:ac:11:00:02"
    command: "/app/run.py"
```

```{note}
MAC address assignment is useful for license-protected software that requires specific MAC addresses.
```

## Custom Arguments

Pass additional arguments to the container engine:

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    command: "/app/run.py"
    custom_args:
      - "--network=host"           # Use host network
      - "--memory=8g"             # Limit memory to 8GB
      - "--cpus=4"               # Limit to 4 CPUs
      - "--gpus=all"             # Use all GPUs
      - "--shm-size=2g"          # Shared memory size
      - "--userns=keep-id"       # Keep user namespace
```

## Complete Example

```yaml
# app_spec.yml

bfabric:
  app_runner: "1.0.0"

versions:
  - version: "1.0.0"
    commands:
      dispatch:
        type: "exec"
        command: "python prepare_config.py"

      process:
        type: "docker"
        image: "proteomics-processor:1.0.0"
        entrypoint: "/usr/bin/python3"
        command: "/app/process.py"
        env:
          APP_VERSION: "${app.version}"
          NUM_WORKERS: "4"
          LOG_LEVEL: "INFO"
        mounts:
          read_only:
            - ["./inputs", "/app/data"]
            - ["/opt/reference", "/app/reference"]
          writeable:
            - ["./outputs", "/app/results"]
          share_bfabric_config: true
        custom_args:
          - "--network=none"  # No network access
          - "--memory=16g"    # 16GB memory
          - "--cpus=8"        # 8 CPUs

      collect:
        type: "exec"
        command: "python finalize.py"
```

## Best Practices

### Use Official Base Images

```yaml
# Good: Based on official Python
image: "python:3.11-slim"

# Avoid: Unmaintained or unofficial
image: "randomuser/python:latest"
```

### Pin Image Versions

```yaml
# Good: Specific version
image: "myapp:1.0.0"

# Avoid: Latest tag (unpredictable)
image: "myapp:latest"
```

### Use Minimal Images

```yaml
# Good: Minimal (smaller, faster)
image: "python:3.11-slim"

# Avoid: Full (larger, slower)
image: "python:3.11"
```

### Separate Read/Write Mounts

```yaml
commands:
  process:
    type: "docker"
    mounts:
      read_only:
        - ["./inputs", "/app/data"]     # Input: read-only
      writeable:
        - ["./outputs", "/app/results"]  # Output: writable
```

### Limit Resources

```yaml
commands:
  process:
    type: "docker"
    custom_args:
      - "--memory=8g"    # Limit memory
      - "--cpus=4"        # Limit CPUs
      - "--disk=20g"      # Limit disk
```

### Isolate Network When Not Needed

```yaml
commands:
  process:
    type: "docker"
    custom_args:
      - "--network=none"  # No network access (safer)
```

### Share B-Fabric Config for API Access

```yaml
commands:
  process:
    type: "docker"
    mounts:
      share_bfabric_config: true
```

## Troubleshooting

### Container Cannot Start

**Issue:** Docker container fails to start

**Solution:**

```bash
# Check Docker daemon
docker ps

# Check image exists
docker images myapp:1.0.0

# Pull image if needed
docker pull myapp:1.0.0

# Test container manually
docker run --rm myapp:1.0.0 /app/run.py
```

### Permission Denied on Mounts

**Issue:** Container cannot access mounted directories

**Solution:**

```bash
# Check directory permissions
ls -la ./inputs
ls -la ./outputs

# Fix permissions
chmod 755 ./inputs
chmod 777 ./outputs

# Or run with user
docker run --user $(id -u):$(id -g) ...
```

### Out of Memory

**Issue:** Container killed due to OOM

**Solution:**

```yaml
# Increase memory limit
commands:
  process:
    type: "docker"
    custom_args:
      - "--memory=16g"  # Increase from 8g

# Or add swap
custom_args:
  - "--memory=8g"
  - "--memory-swap=16g"  # 8GB RAM + 8GB swap
```

### Cannot Access B-Fabric from Container

**Issue:** Container cannot connect to B-Fabric

**Solution:**

```yaml
# Ensure config sharing is enabled
commands:
  process:
    type: "docker"
    mounts:
      share_bfabric_config: true

# Use network access if needed
custom_args:
  - "--network=host"  # Use host network
```

### Docker Image Not Found

**Issue:** Image pull fails

**Solution:**

```bash
# Check image name
docker pull myapp:1.0.0

# List available images
docker images

# Verify registry access
docker login registry.example.com
```

## Advanced: Multi-Stage Builds

For complex applications, use multi-stage Dockerfiles:

```dockerfile
# Stage 1: Build stage
FROM python:3.11-slim as builder
RUN pip install numpy pandas scipy

# Stage 2: Runtime stage
FROM python:3.11-slim
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
WORKDIR /app
COPY run.py /app/
CMD ["/usr/bin/python3", "/app/run.py"]
```

Build and push:

```bash
docker build -t registry.com/myapp:1.0.0 .
docker push registry.com/myapp:1.0.0
```

## Next Steps

- **[Python Environment](../execution/python_environment.md)** - Python virtual environments
- **[Complete Workflow](../workflows/complete_workflow.md)** - End-to-end example
- **[Shell Environment](../execution/shell_environment.md)** - Direct shell execution

## Related Documentation

- [Quick Start Tutorial](../../getting_started/quick_start.md) - Hands-on introduction
- [Defining Commands](../creating_an_app/defining_commands.md) - Command configuration
- [Complete Workflow](../workflows/complete_workflow.md)\*\* - Full workflow example

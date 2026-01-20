# bfabric-cli Reference

The `bfabric-cli` command-line interface provides convenient access to B-Fabric functionality without writing Python code. It's particularly useful for:

- Quick one-off queries and operations
- Batch processing in shell scripts
- Interactive data exploration
- Testing API calls
- System administration tasks

## Prerequisites

- **Installation**: Install the `bfabric-scripts` package. See the [Installation Guide](../../getting_started/installation.md).
- **Configuration**: Set up your credentials in `~/.bfabricpy.yml`. See the [Configuration Guide](../../getting_started/configuration.md).

## Command Overview

bfabric-cli organizes commands by functionality:

### Core Commands

| Command                  | Purpose                                                |
| ------------------------ | ------------------------------------------------------ |
| `bfabric-cli api`        | Generic CRUD operations on B-Fabric entities           |
| `bfabric-cli dataset`    | Dataset-specific operations (read, upload, download)   |
| `bfabric-cli executable` | Executable operations (show, upload, dump)             |
| `bfabric-cli workunit`   | Workunit operations (check status, export definitions) |
| `bfabric-cli feeder`     | Feeder operations for creating importresources         |

### Legacy/Deprecated

| Command                    | Status                                         |
| -------------------------- | ---------------------------------------------- |
| `bfabric-cli external-job` | Transitory - will be removed in future release |

## Getting Help

Explore the command hierarchy using `--help`:

```bash
# Show all top-level commands
bfabric-cli --help

# Show api subcommands
bfabric-cli api --help

# Show specific command details
bfabric-cli api read --help
```

## Common Patterns

### Using Named Parameters

While many parameters can be passed positionally, using named parameters is recommended for clarity and future compatibility:

```bash
# Recommended (explicit)
bfabric-cli api read resource --limit 10

# Also works (positional)
bfabric-cli api read resource 10
```

### Specifying Multiple Values

For query parameters that accept multiple values, repeat the key-value pair:

```bash
# Query multiple IDs
bfabric-cli api read resource id 12345 id 12346 id 12347
```

### Output Formats

Most commands support multiple output formats:

```bash
# Interactive table (default)
bfabric-cli api read resource --format table-rich

# JSON
bfabric-cli api read resource --format json

# YAML
bfabric-cli api read resource --format yaml

# TSV (tab-separated values)
bfabric-cli api read resource --format tsv
```

### Saving Output

Use `--file` to save output to a file:

```bash
bfabric-cli api read resource --limit 100 --format json --file results.json
```

### Python Equivalence

The `api read` command displays the equivalent Python code, making it easy to transition from CLI to Python:

```bash
bfabric-cli api read resource --limit 10
# Outputs: results = client.read(endpoint='resource', obj={}, max_results=100)
```

## Confirmation Prompts

Destructive operations (`update`, `delete`) require confirmation:

```bash
bfabric-cli api update workunit 12345 description "Updated description"
# Prompts: Do you want to proceed with the update? [y/N]

# Skip confirmation (use with caution!)
bfabric-cli api update workunit 12345 description "Updated description" --no-confirm
```

## Command Documentation

```{toctree}
:maxdepth: 1
api_operations
datasets
executables
workunits
feeder
```

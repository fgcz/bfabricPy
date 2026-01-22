# API Operations

The `bfabric-cli api` command provides generic CRUD (Create, Read, Update, Delete) operations on all B-Fabric entity types from the command line.

```{note}
Use the CLI when you need quick one-off operations, want to test API calls, or prefer working from the terminal. For complex workflows, automated processing, or programmatic logic, use the [Python API](../../api_reference/) instead.
```

## Overview

```bash
bfabric-cli api --help
```

| Subcommand | Purpose |
| ---------- | --------------------------- |
| `create` | Create new entities |
| `read` | Query and retrieve entities |
| `update` | Modify existing entities |
| `delete` | Remove entities |
| `inspect` | Inspect SOAP API structure |

## Reading Entities

### Basic Usage

```bash
bfabric-cli api read [ENDPOINT] [QUERY] [OPTIONS]
```

### Parameters

| Parameter | Required | Description |
| ----------- | -------- | ------------------------------------------------------------------- |
| `endpoint` | Yes | Entity type (e.g., `resource`, `sample`, `workunit`, `dataset`) |
| `query` | No | Key-value pairs to filter results |
| `--format` | No | Output: `json`, `yaml`, `tsv`, `table-rich` (default: `table-rich`) |
| `--limit` | No | Maximum results (default: 100) |
| `--columns` | No | Comma-separated columns to display |
| `--file` | No | Write output to file |

### Examples

```bash
# List recent resources
bfabric-cli api read resource --limit 10

# Filter by columns
bfabric-cli api read resource --limit 10 --columns id,name,relativepath

# Query by multiple criteria
bfabric-cli api read resource createdby pfeeder createdafter 2024-05-01

# Query multiple IDs
bfabric-cli api read resource id 2784586 id 2784576

# Output formats
bfabric-cli api read resource --limit 10 --format json
bfabric-cli api read resource --limit 10 --format tsv

# Save to file
bfabric-cli api read resource --limit 100 --format json --file results.json
```

## Creating Entities

### Basic Usage

```bash
bfabric-cli api create [ENDPOINT] [ATTRIBUTES]
```

### Examples

```bash
# Create a resource
bfabric-cli api create resource name "hello.txt" workunitid 321802 base64 aGVsbG8=

# Create a sample
bfabric-cli api create sample name "My Sample" containerid 1234
```

## Updating Entities

### Basic Usage

```bash
bfabric-cli api update [ENDPOINT] [ENTITY_ID] [ATTRIBUTES]
```

### Examples

```bash
# Update a workunit
bfabric-cli api update workunit 321802 description "Updated description"

# Update multiple attributes
bfabric-cli api update sample 12345 name "New Name" description "Updated"

# Skip confirmation (use with caution!)
bfabric-cli api update resource 12345 name "New Name" --no-confirm
```

## Deleting Entities

### Basic Usage

```bash
bfabric-cli api delete [ENDPOINT] [ID] [OPTIONS]
```

### Examples

```bash
# Delete a single entity
bfabric-cli api delete resource 12345

# Delete multiple entities
bfabric-cli api delete resource 12345 12346 12347

# Skip confirmation (dangerous!)
bfabric-cli api delete resource 12345 --no-confirm
```

## Inspecting API Structure

For detailed information about discovering endpoints and understanding API structure, see [API Inspection](api_inspection.md).

```bash
# Quick inspect
bfabric-cli api inspect [ENDPOINT] [METHOD]
```

## Common Entity Types

| Endpoint | Description |
| ---------------- | ----------------------- |
| `resource` | File resources |
| `sample` | Samples |
| `workunit` | Workunits/jobs |
| `dataset` | Datasets |
| `project` | Projects |
| `container` | Containers |
| `application` | Applications |
| `executable` | Application executables |
| `importresource` | Import resources |

## Tips

1. **Test with small limits first**: `bfabric-cli api read resource --limit 5`
2. **Use named parameters**: `--limit 10` is clearer than positional `10`
3. **Save output**: `--file results.json` for further processing
4. **Check Python equivalence**: CLI shows the equivalent Python code on stderr

## See Also

- [Python API: Writing Data](../writing_data/index.md) - Programmatic write operations
- [CLI Reference: Datasets](datasets.md) - Dataset-specific operations
- [CLI Reference: Workunits](workunits.md) - Workunit-specific operations

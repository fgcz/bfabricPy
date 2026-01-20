# API Operations

The `bfabric-cli api` command provides generic CRUD (Create, Read, Update, Delete) operations on all B-Fabric entity types.

## Overview

```bash
bfabric-cli api --help
```

Available subcommands:

| Subcommand | Purpose                     |
| ---------- | --------------------------- |
| `create`   | Create new entities         |
| `read`     | Query and retrieve entities |
| `update`   | Modify existing entities    |
| `delete`   | Remove entities             |
| `inspect`  | Inspect SOAP API structure  |

______________________________________________________________________

## Reading Entities

Query and retrieve entities from B-Fabric.

### Basic Usage

```bash
bfabric-cli api read [ENDPOINT] [QUERY] [OPTIONS]
```

### Parameters

| Parameter           | Required | Description                                                                |
| ------------------- | -------- | -------------------------------------------------------------------------- |
| `endpoint`          | Yes      | Entity type (e.g., `resource`, `sample`, `workunit`, `dataset`)            |
| `query`             | No       | Key-value pairs to filter results (repeat for multiple values)             |
| `--format`          | No       | Output format: `json`, `yaml`, `tsv`, `table-rich` (default: `table-rich`) |
| `--limit`           | No       | Maximum number of results (default: 100)                                   |
| `--columns`         | No       | Comma-separated list of columns to display                                 |
| `--cli-max-columns` | No       | Max columns in table format (default: 7)                                   |
| `--file`            | No       | Write output to specified file                                             |

### Examples

**List recent resources:**

```bash
bfabric-cli api read resource --limit 10
```

**Filter by specific columns:**

```bash
bfabric-cli api read resource --limit 10 \
    --columns id,name,relativepath,description,filechecksum
```

**Query by multiple criteria:**

```bash
bfabric-cli api read resource \
    createdby pfeeder \
    createdafter 2024-05-01 \
    createdbefore 2024-05-02 \
    --columns id,relativepath,createdby
```

**Query multiple IDs:**

```bash
bfabric-cli api read resource id 2784586 id 2784576 id 2784573
```

**Output formats:**

```bash
# JSON
bfabric-cli api read resource --limit 10 --format json

# YAML
bfabric-cli api read resource --limit 10 --format yaml

# TSV
bfabric-cli api read resource --limit 10 --format tsv
```

**Save to file:**

```bash
bfabric-cli api read resource --limit 100 --format json --file results.json
```

### Output Notes

- The command displays the equivalent Python query code (on stderr)
- For table format, IDs are clickable links to the B-Fabric web interface
- Results are sorted by ID

______________________________________________________________________

## Creating Entities

Create new entities in B-Fabric.

### Basic Usage

```bash
bfabric-cli api create [ENDPOINT] [ATTRIBUTES]
```

### Parameters

| Parameter    | Required | Description                        |
| ------------ | -------- | ---------------------------------- |
| `endpoint`   | Yes      | Entity type to create              |
| `attributes` | No       | Key-value pairs for the new entity |

### Examples

**Create a resource:**

```bash
bfabric-cli api create resource \
    name "hello_world.txt" \
    workunitid 321802 \
    base64 aGVsbG8gd29ybGQ=
```

**Create a sample:**

```bash
bfabric-cli api create sample \
    name "My Sample" \
    containerid 1234
```

### Notes

- The `id` attribute cannot be specified (it's auto-generated)
- The operation performs no confirmation (creates immediately)
- Output shows the created entity with its new ID

______________________________________________________________________

## Updating Entities

Modify existing entities in B-Fabric.

### Basic Usage

```bash
bfabric-cli api update [ENDPOINT] [ENTITY_ID] [ATTRIBUTES] [OPTIONS]
```

### Parameters

| Parameter      | Required | Description                           |
| -------------- | -------- | ------------------------------------- |
| `endpoint`     | Yes      | Entity type to update                 |
| `entity_id`    | Yes      | ID of the entity to update            |
| `attributes`   | No       | Key-value pairs to modify             |
| `--no-confirm` | No       | Skip confirmation prompt (dangerous!) |

### Examples

**Update a workunit description:**

```bash
bfabric-cli api update workunit 321802 description "Updated description"
```

**Update multiple attributes:**

```bash
bfabric-cli api update sample 12345 \
    name "New Name" \
    description "Updated description"
```

**Skip confirmation:**

```bash
bfabric-cli api update resource 12345 name "New Name" --no-confirm
```

### Confirmation Prompt

Before updating, you'll see:

1. The current entity state
2. The attributes that will be updated
3. A prompt: `Do you want to proceed with the update? [y/N]`

### Notes

- The `id` in attributes is ignored (must specify via `entity_id`)
- Use `--no-confirm` only in automated scripts
- Operation is considered destructive, hence confirmation

______________________________________________________________________

## Deleting Entities

Remove entities from B-Fabric.

### Basic Usage

```bash
bfabric-cli api delete [ENDPOINT] [ID] [OPTIONS]
```

### Parameters

| Parameter      | Required | Description                           |
| -------------- | -------- | ------------------------------------- |
| `endpoint`     | Yes      | Entity type to delete                 |
| `id`           | Yes      | One or more entity IDs to delete      |
| `--no-confirm` | No       | Skip confirmation prompt (dangerous!) |

### Examples

**Delete a single entity:**

```bash
bfabric-cli api delete resource 12345
```

**Delete multiple entities:**

```bash
bfabric-cli api delete resource 12345 12346 12347
```

**Skip confirmation:**

```bash
bfabric-cli api delete resource 12345 --no-confirm
```

### Confirmation Prompt

Before each deletion, you'll see:

1. The entity details
2. A prompt: `Delete resource with ID 12345? [y/N]`

### Notes

- Multiple IDs can be deleted in one command
- If an entity doesn't exist, a warning is shown
- Each ID is confirmed separately (unless `--no-confirm`)

______________________________________________________________________

## Inspecting API Structure

Inspect the parameter structure of B-Fabric's SOAP API methods.

### Basic Usage

```bash
bfabric-cli api inspect [ENDPOINT] [METHOD] [OPTIONS]
```

### Parameters

| Parameter     | Required | Description                                           |
| ------------- | -------- | ----------------------------------------------------- |
| `endpoint`    | Yes      | Entity type to inspect                                |
| `method`      | No       | API method name (default: `read`)                     |
| `--max-depth` | No       | Maximum recursion depth for nested types (default: 5) |

### Examples

**Inspect the read method:**

```bash
bfabric-cli api inspect resource
```

**Inspect the save method:**

```bash
bfabric-cli api inspect resource save
```

**Custom depth:**

```bash
bfabric-cli api inspect workunit --max-depth 3
```

### Output

The inspection shows:

- Namespaces used in the method signature
- Parameters with their types
- Nested field structure
- Required fields (marked with `*`)

### Notes

- Information is read from the SOAP API
- May not directly translate to BfabricPy functionality
- Useful for understanding the underlying B-Fabric structure

______________________________________________________________________

## Common Entity Types

Common endpoints you can use:

| Endpoint         | Description             |
| ---------------- | ----------------------- |
| `resource`       | File resources          |
| `sample`         | Samples                 |
| `workunit`       | Workunits/jobs          |
| `dataset`        | Datasets                |
| `project`        | Projects                |
| `container`      | Containers              |
| `application`    | Applications            |
| `executable`     | Application executables |
| `importresource` | Import resources        |

______________________________________________________________________

## Tips and Best Practices

### Always Test First

```bash
# Test your query with a small limit first
bfabric-cli api read resource --limit 5 --format json

# Then scale up
bfabric-cli api read resource --limit 1000 --format json --file all_resources.json
```

### Use Named Parameters

```bash
# Clear and future-proof
bfabric-cli api read resource --limit 10

# Works but less clear
bfabric-cli api read resource 10
```

### Save Output for Analysis

```bash
# Save for further processing
bfabric-cli api read workunit --format json --file workunits.json
```

### Pipeline-Friendly

```bash
# Pipe to other tools (main output only)
bfabric-cli api read resource --format tsv | head -10
```

______________________________________________________________________

## See Also

- [Datasets](datasets.md) - Dataset-specific operations
- [Workunits](workunits.md) - Workunit-specific operations
- [Python API Reference](../../api_reference/) - Using bfabric in Python

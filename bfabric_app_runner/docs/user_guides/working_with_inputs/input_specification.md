# Input Specification

This guide covers defining inputs in `inputs.yml` to specify data that your application needs.

## Overview

The input specification (`inputs.yml`) defines the input files your application requires, including:

- Input sources (B-Fabric datasets, resources, local files, static files)
- File names and locations
- Integrity checking and caching
- Optional filters for specific inputs

## Input Specification Structure

```yaml
inputs:
  - type: <input_type>
    <type_specific_fields>
    filename: <target_filename>
```

### Available Input Types

bfabric-app-runner supports multiple input types:

| Type | Source | Use Case |
| ----------------------- | ----------------------------------- | --------------------------------------------------- |
| **bfabric_dataset** | B-Fabric dataset | Tabular data (CSV, TSV) |
| **bfabric_resource** | B-Fabric resource file | Any file stored in B-Fabric |
| **bfabric_annotation** | B-Fabric annotation | Genome/proteome annotations |
| **bfabric_order_fasta** | B-Fabric order FASTA | FASTA sequences |
| **bfabric_resource_dataset** | B-Fabric resource (dataset flow) | Dataset as resource |
| **bfabric_resource_archive** | B-Fabric resource archive | Compressed archives |
| **file** | Local file or SSH file | Files from local filesystem or remote server |
| **static_file** | Embedded content | Small config/template files |
| **static_yaml** | Embedded YAML content | Small configuration files |

## B-Fabric Dataset

Download a dataset from B-Fabric:

```yaml
inputs:
  - type: bfabric_dataset
    id: 12345
    filename: data.csv
    separator: ","
```

**Options:**

| Field | Type | Required | Description |
| ---------- | ------ | -------- | ------------------------------------ |
| **type** | string | Yes | Must be `bfabric_dataset` |
| **id** | integer | Yes | Dataset ID in B-Fabric |
| **filename** | string | Yes | Local filename to save as |
| **separator** | string | No | CSV separator (default: `,`) |

**Example:**

```yaml
inputs:
  - type: bfabric_dataset
    id: 53706
    filename: sample_data.csv
    separator: "\t"  # Tab-separated file
```

## B-Fabric Resource

Download a resource file from B-Fabric:

```yaml
inputs:
  - type: bfabric_resource
    id: 2700958
    filename: reference_genome.fasta
    check_checksum: true
```

**Options:**

| Field | Type | Required | Description |
| ---------------- | ------- | -------- | -------------------------------------------------- |
| **type** | string | Yes | Must be `bfabric_resource` |
| **id** | integer | Yes | Resource ID in B-Fabric |
| **filename** | string | Yes | Local filename to save as |
| **check_checksum** | boolean | No | Verify checksum (default: `true`) |

**Example:**

```yaml
inputs:
  - type: bfabric_resource
    id: 2700958
    filename: reference.fasta
    check_checksum: false  # Skip checksum verification
```

## B-Fabric Annotation

Download an annotation from B-Fabric:

```yaml
inputs:
  - type: bfabric_annotation
    id: 12345
    filename: annotation.gff
```

**Options:**

| Field | Type | Required | Description |
| ---------- | ------ | -------- | -------------------------------------------- |
| **type** | string | Yes | Must be `bfabric_annotation` |
| **id** | integer | Yes | Annotation ID in B-Fabric |
| **filename** | string | Yes | Local filename to save as |

## B-Fabric Order FASTA

Download FASTA sequences from a B-Fabric order:

```yaml
inputs:
  - type: bfabric_order_fasta
    id: 67890
    filename: sequences.fasta
```

**Options:**

| Field | Type | Required | Description |
| ---------- | ------ | -------- | -------------------------------------------- |
| **type** | string | Yes | Must be `bfabric_order_fasta` |
| **id** | integer | Yes | Order ID in B-Fabric |
| **filename** | string | Yes | Local filename to save as |

## Local File

Use a file from local filesystem:

```yaml
inputs:
  - type: file
    source:
      local: "/path/to/local/file.txt"
    filename: input.txt
    link: false
    checksum: "abc123"
```

**Options:**

| Field | Type | Required | Description |
| ---------- | --------------- | -------- | -------------------------------------------- |
| **type** | string | Yes | Must be `file` |
| **source** | FileSourceLocal | FileSourceSsh | Yes | File source (local or SSH) |
| **filename** | string | No | Local filename (default: source filename) |
| **link** | boolean | No | Create symlink instead of copy (default: `false`) |
| **checksum** | string | No | Expected checksum for verification |

**Local Source:**

```yaml
inputs:
  - type: file
    source:
      local: "/data/reference/genome.fasta"
    filename: reference.fasta
```

**SSH Source:**

```yaml
inputs:
  - type: file
    source:
      ssh:
        host: "server.example.com"
        path: "/data/file.txt"
    filename: input.txt
```

## Static File

Embed file content directly in YAML:

```yaml
inputs:
  - type: static_file
    content: "version: 1.0.0\nmode: production"
    filename: config.txt
```

**Options:**

| Field | Type | Required | Description |
| -------- | ------------ | -------- | ------------------------------------------------ |
| **type** | string | Yes | Must be `static_file` |
| **content** | string/bytes | Yes | Text or binary content to write |
| **filename** | string | Yes | Target filename |

**Example:**

```yaml
# Create a JSON configuration file
inputs:
  - type: static_file
    content: |
      {
        "version": "1.0.0",
        "data_dir": "/app/data",
        "output_dir": "/app/output"
      }
    filename: config.json
```

## Multiple Inputs

Define multiple inputs in a single file:

```yaml
inputs:
  # Dataset from B-Fabric
  - type: bfabric_dataset
    id: 12345
    filename: data.csv

  # Resource from B-Fabric
  - type: bfabric_resource
    id: 67890
    filename: reference.fasta

  # Static configuration file
  - type: static_file
    content: "threads: 4\nmemory: 8g"
    filename: config.txt

  # Local file
  - type: file
    source:
      local: "/data/parameters.json"
    filename: params.json
```

## Validating Input Specifications

Validate your input specification before using it:

```bash
bfabric-app-runner validate inputs-spec inputs.yml
```

Expected output:

```
InputsSpec(
  inputs=[
    DatasetSpec(type='bfabric_dataset', id=12345, filename='data.csv', separator=','),
    ResourceSpec(type='bfabric_resource', id=67890, filename='reference.fasta', check_checksum=True),
    StaticFileSpec(type='static_file', content='...', filename='config.txt'),
    FileSpec(type='file', source=FileSourceLocal(local='/data/parameters.json'), filename='params.json')
  ]
)
```

## Staging Input Files

After defining inputs, stage (download/prepare) them:

```bash
# List what will be prepared
bfabric-app-runner inputs list inputs.yml .

# Prepare (download) input files
bfabric-app-runner inputs prepare inputs.yml .

# Check if files are up-to-date
bfabric-app-runner inputs check inputs.yml .

# Clean up (remove) input files
bfabric-app-runner inputs clean inputs.yml .
```

See [Staging Files](./staging_files.md) for details.

## Best Practices

### Use Descriptive Filenames

```yaml
# Good: Descriptive filename
- type: bfabric_dataset
    filename: sample_2024_proteomics.csv

# Avoid: Generic filename
- type: bfabric_dataset
    filename: data.csv
```

### Verify Checksums for Critical Data

```yaml
inputs:
  - type: bfabric_resource
    id: 12345
    filename: reference_genome.fasta
    check_checksum: true  # Critical data should be verified
```

### Use Static Files for Small Configs

```yaml
# Good: Small config as static file
- type: static_file
    content: "version: 1.0.0"
    filename: config.txt

# Avoid: Separate file for small configs
- type: file
    source:
      local: "./config.txt"
    filename: config.txt
```

### Group Related Inputs

```yaml
inputs:
  # Main data
  - type: bfabric_dataset
    id: 12345
    filename: raw_data.csv

  # Reference data
  - type: bfabric_resource
    id: 67890
    filename: reference_genome.fasta

  # Annotations
  - type: bfabric_annotation
    id: 11111
    filename: annotations.gff
```

## Next Steps

- **[Staging Files](./staging_files.md)** - Download and prepare input files
- **[B-Fabric Datasets](./bfabric_datasets.md)** - Working with datasets
- **[B-Fabric Resources](./bfabric_resources.md)** - Working with resources
- **[Static Files](./static_files.md)** - Embedding files

## Related Documentation

- [Quick Start Tutorial](../../getting_started/quick_start.md) - Hands-on introduction
- [API Reference](../../api_reference/input_specification.md) - Complete input type documentation
- [Staging Files](./staging_files.md) - Preparing input files

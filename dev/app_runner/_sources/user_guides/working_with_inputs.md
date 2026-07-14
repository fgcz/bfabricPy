# Working with Inputs

This guide covers how bfabric-app-runner handles input files: specification, resolution, preparation, and management.

## Overview

The input system follows a two-phase pipeline:

1. **Resolution**: Input specifications (from YAML) are converted into standardized resolved types.
2. **Preparation**: Resolved inputs are fetched, generated, or linked into the working directory.

This separation keeps the "what to process" logic independent from "how to process it", making the system extensible and testable.

## Input YAML Format

Inputs are defined in a YAML file (typically `inputs.yml`) under a top-level `inputs:` key, whose value
is a list of specifications:

```yaml
inputs:
  - type: bfabric_resource
    id: 12345
    filename: input_data.raw
    check_checksum: true

  - type: static_file
    content: "sample_id,condition\n1,control\n2,treated"
    filename: metadata.csv

  - type: bfabric_dataset
    id: 6789
    filename: samples.csv
    separator: ","
```

Each entry must include a `type` field that determines which resolver handles it.

## Input Spec Types

Each type is shown below with a representative example. For the complete field reference — every option,
its type, and default — see the [Input specification](../specs/input_specification.md).

### bfabric_resource

Downloads a resource file from B-Fabric.

```yaml
inputs:
  - type: bfabric_resource
    id: 12345
    filename: data.raw
    check_checksum: true
```

### bfabric_dataset

Downloads a dataset from B-Fabric as a tabular file.

```yaml
inputs:
  - type: bfabric_dataset
    id: 6789
    filename: samples.csv
    separator: ","
    format: csv
```

### bfabric_resource_archive

Downloads a resource and extracts it as an archive.

```yaml
inputs:
  - type: bfabric_resource_archive
    id: 12345
    filename: extracted_data
    extract: zip
    include_patterns:
      - "*.mzML"
    strip_root: true
    check_checksum: true
```

### bfabric_resource_dataset

Downloads multiple resources referenced in a dataset column. The optional manifest
(`output_dataset_filename`) is always written as Parquet, regardless of the extension you give it.

```yaml
inputs:
  - type: bfabric_resource_dataset
    id: 100
    column: Resource
    filename: "{name}.raw"
    check_checksum: true
    output_dataset_filename: manifest.parquet
    output_dataset_file_column: local_path
```

### bfabric_order_fasta

Downloads FASTA data associated with an order or workunit.

```yaml
inputs:
  - type: bfabric_order_fasta
    id: 500
    entity: workunit
    filename: sequences.fasta
    required: true
```

### bfabric_annotation

Downloads annotation data linking resources to samples.

```yaml
inputs:
  - type: bfabric_annotation
    annotation: resource_sample
    filename: annotations.csv
    separator: ","
    resource_ids:
      - 100
      - 200
```

### file

Copies or links a file from a local or SSH source (an HTTP source is also supported — see the
[Input specification](../specs/input_specification.md)).

```yaml
inputs:
  # Local file
  - type: file
    source:
      local: /data/reference/genome.fa
    filename: genome.fa
    link: true

  # SSH file
  - type: file
    source:
      ssh:
        host: server.example.com
        path: /data/reference/genome.fa
    filename: genome.fa
    checksum: abc123...
```

### static_file

Creates a file with inline content.

```yaml
inputs:
  - type: static_file
    content: "key=value\nother=setting"
    filename: config.ini
```

### static_yaml

Creates a YAML file from inline structured data.

```yaml
inputs:
  - type: static_yaml
    data:
      param1: 100
      param2: "hello"
      items:
        - a
        - b
    filename: params.yml
```

## Resolution Pipeline

When inputs are processed, the resolver converts each spec into one of three resolved types:

- **ResolvedFile**: A file with a source location (local or SSH).
- **ResolvedStaticFile**: In-memory content to be written directly.
- **ResolvedDirectory**: A directory with source location and extraction options.

The resolved inputs are then passed to the preparation phase, which fetches, copies, or writes each one into the working directory.

## CLI Commands

### Prepare inputs

Download and prepare all input files:

```bash
bfabric-app-runner inputs prepare inputs.yml [target_folder]
```

`inputs_yaml`
: Path to the inputs YAML file.

`target_folder`
: Optional. Working directory for prepared files (defaults to current directory).

`--ssh-user`
: SSH user for remote file access.

`--filter`
: Only prepare inputs matching the given filename pattern.

### List inputs

Show all defined inputs and their status:

```bash
bfabric-app-runner inputs list inputs.yml [target_folder]
```

`--check`
: Also verify whether each input file exists in the target folder.

### Check inputs

Verify that all inputs are present:

```bash
bfabric-app-runner inputs check inputs.yml [target_folder]
```

### Clean inputs

Remove prepared input files:

```bash
bfabric-app-runner inputs clean inputs.yml [target_folder]
```

`--filter`
: Only clean inputs matching the given filename pattern.

## Filtering

The `--filter` flag on `inputs prepare` and `inputs clean` accepts a filename pattern to selectively process inputs:

```bash
# Only prepare a specific file
bfabric-app-runner inputs prepare inputs.yml --filter "genome.fa"

# Clean specific files
bfabric-app-runner inputs clean inputs.yml --filter "*.raw"
```

## Validating Input Specs

You can validate an inputs YAML file without executing it:

```bash
bfabric-app-runner validate inputs-spec inputs.yml
```

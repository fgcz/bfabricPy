# Working with Inputs

This guide covers how bfabric-app-runner handles input files: specification, resolution, preparation, and management.

## Overview

The input system follows a two-phase pipeline:

1. **Resolution**: Input specifications (from YAML) are converted into standardized resolved types.
2. **Preparation**: Resolved inputs are fetched, generated, or linked into the working directory.

This separation keeps the "what to process" logic independent from "how to process it", making the system extensible and testable.

## Input YAML Format

Inputs are defined in a YAML file (typically `inputs.yml`) as a list of specifications:

```yaml
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

### bfabric_resource

Downloads a resource file from B-Fabric.

```yaml
- type: bfabric_resource
  id: 12345
  filename: data.raw
  check_checksum: true
```

`id` (int)
: B-Fabric resource ID.

`filename` (str)
: Target filename in the working directory.

`check_checksum` (bool, optional)
: Verify the file checksum after download.

### bfabric_dataset

Downloads a dataset from B-Fabric as a tabular file.

```yaml
- type: bfabric_dataset
  id: 6789
  filename: samples.csv
  separator: ","
  format: csv
```

`id` (int)
: B-Fabric dataset ID.

`filename` (str)
: Target filename.

`separator` (str, optional)
: Column separator character.

`format` (str, optional)
: Output format: `"csv"` or `"parquet"`.

### bfabric_resource_archive

Downloads a resource and extracts it as an archive.

```yaml
- type: bfabric_resource_archive
  id: 12345
  filename: extracted_data
  extract: zip
  include_patterns:
    - "*.mzML"
  strip_root: true
  check_checksum: true
```

`id` (int)
: B-Fabric resource ID.

`filename` (str)
: Target directory name.

`extract` (str)
: Archive format. Currently only `"zip"` is supported.

`include_patterns` (list of str, optional)
: Glob patterns for files to include from the archive.

`exclude_patterns` (list of str, optional)
: Glob patterns for files to exclude from the archive.

`strip_root` (bool, optional)
: Remove the root directory from extracted paths.

`check_checksum` (bool, optional)
: Verify the resource checksum.

### bfabric_resource_dataset

Downloads multiple resources referenced in a dataset column.

```yaml
- type: bfabric_resource_dataset
  id: 100
  column: resource_id
  filename: "{name}.raw"
  check_checksum: true
  output_dataset_filename: manifest.csv
  output_dataset_file_column: local_path
```

`id` (int)
: B-Fabric dataset ID containing resource references.

`column` (str)
: Column name containing resource IDs.

`filename` (str)
: Filename template for downloaded resources.

`include_patterns` / `exclude_patterns` (list of str, optional)
: Filter which resources to download.

`check_checksum` (bool, optional)
: Verify checksums.

`output_dataset_filename` (str, optional)
: Write an output dataset mapping resources to local paths.

`output_dataset_file_column` (str, optional)
: Column name for local file paths in the output dataset.

`output_dataset_only` (bool, optional)
: Only generate the output dataset without downloading files.

### bfabric_order_fasta

Downloads FASTA data associated with an order or workunit.

```yaml
- type: bfabric_order_fasta
  id: 500
  entity: workunit
  filename: sequences.fasta
  required: true
```

`id` (int)
: Entity ID.

`entity` (str)
: Entity type: `"workunit"` or `"order"`.

`filename` (str)
: Target filename.

`required` (bool, optional)
: Whether the FASTA must exist (raises error if missing and required).

### bfabric_annotation

Downloads annotation data linking resources to samples.

```yaml
- type: bfabric_annotation
  annotation: resource_sample
  filename: annotations.csv
  separator: ","
  resource_ids:
    - 100
    - 200
```

`annotation` (str)
: Annotation type. Currently `"resource_sample"`.

`filename` (str)
: Target filename.

`separator` (str, optional)
: Column separator.

`resource_ids` (list of int, optional)
: Specific resource IDs to include.

`format` (str, optional)
: Output format.

### file

Copies or links a file from a local or SSH source.

```yaml
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

`source` (object)
: Either `{local: path}` or `{ssh: {host, path}}`.

`filename` (str)
: Target filename.

`link` (bool, optional)
: Create a symlink instead of copying (local sources only).

`checksum` (str, optional)
: Expected file checksum for verification.

### static_file

Creates a file with inline content.

```yaml
- type: static_file
  content: "key=value\nother=setting"
  filename: config.ini
```

`content` (str or bytes)
: File content to write.

`filename` (str)
: Target filename.

### static_yaml

Creates a YAML file from inline structured data.

```yaml
- type: static_yaml
  data:
    param1: 100
    param2: "hello"
    items:
      - a
      - b
  filename: params.yml
```

`data` (dict or list)
: Data to serialize as YAML.

`filename` (str)
: Target filename.

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

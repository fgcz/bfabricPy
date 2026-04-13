# Working with Outputs

This guide covers how to register processing results back into B-Fabric using bfabric-app-runner.

## Overview

After an app finishes processing, its output files and datasets need to be registered in B-Fabric. The output system supports three types of output specifications, defined in an `outputs.yml` file.

## Output YAML Format

```yaml
- type: bfabric_copy_resource
  local_path: results/output.raw
  store_entry_path: output.raw

- type: bfabric_dataset
  local_path: results/summary.csv
  separator: ","
  name: "Results Summary"

- type: bfabric_link
  name: "Analysis Report"
  url: "https://example.com/report/123"
```

## Output Spec Types

### bfabric_copy_resource

Copies a local file to the B-Fabric storage and registers it as a resource.

```yaml
- type: bfabric_copy_resource
  local_path: results/output.mzML
  store_entry_path: output.mzML
  store_folder_path: /path/in/store
  update_existing: NO
  protocol: scp
```

`local_path` (str, required)
: Path to the local file (relative to the chunk directory).

`store_entry_path` (str, optional)
: Filename in the B-Fabric storage.

`store_folder_path` (str, optional)
: Directory path within the storage.

`update_existing` (str, optional)
: How to handle existing resources. See [UpdateExisting](#updateexisting-behavior) below.

`protocol` (str, optional)
: Transfer protocol. Currently `"scp"`.

### bfabric_dataset

Registers a local tabular file as a B-Fabric dataset.

```yaml
- type: bfabric_dataset
  local_path: results/summary.csv
  separator: ","
  name: "Experiment Results"
  has_header: true
  invalid_characters: remove
```

`local_path` (str, required)
: Path to the local CSV/TSV file.

`separator` (str, optional)
: Column separator character.

`name` (str, optional)
: Display name for the dataset in B-Fabric.

`has_header` (bool, optional)
: Whether the file has a header row.

`invalid_characters` (str, optional)
: How to handle invalid characters.

### bfabric_link

Creates a link resource in B-Fabric pointing to an external URL.

```yaml
- type: bfabric_link
  name: "Interactive Report"
  url: "https://example.com/report/456"
  update_existing: IF_EXISTS
```

`name` (str, required)
: Display name for the link.

`url` (str, required)
: The URL to link to.

`entity_type` (str, optional)
: B-Fabric entity type to associate the link with.

`entity_id` (int, optional)
: B-Fabric entity ID to associate the link with.

`update_existing` (str, optional)
: How to handle existing links. See [UpdateExisting](#updateexisting-behavior) below.

## UpdateExisting Behavior

The `update_existing` field controls what happens when a resource or link with the same identity already exists in B-Fabric:

`NO`
: Do not update. Create a new resource (default behavior).

`IF_EXISTS`
: Update the existing resource if one is found; otherwise create a new one.

`REQUIRED`
: The resource must already exist. Raises an error if not found.

## CLI Commands

### Register all outputs

Register all outputs defined in an outputs YAML file:

```bash
bfabric-app-runner outputs register outputs.yml workunit_ref
```

`outputs_yaml`
: Path to the outputs YAML file.

`workunit_ref`
: The workunit reference (ID or URI).

`--ssh-user`
: SSH user for remote file transfers.

`--force-storage`
: Override the storage location.

`--reuse-default-resource`
: Reuse the default resource for the workunit.

### Register a single file

Register a single output file without an outputs YAML:

```bash
bfabric-app-runner outputs register-single-file results/output.mzML \
  --workunit-ref 12345 \
  --store-entry-path output.mzML
```

`local_path`
: Path to the local file.

`--workunit-ref` (required)
: The workunit reference.

`--store-entry-path`
: Filename in the B-Fabric storage.

`--store-folder-path`
: Directory path within the storage.

`--update-existing`
: UpdateExisting behavior (`NO`, `IF_EXISTS`, or `REQUIRED`).

`--ssh-user`
: SSH user for remote transfers.

`--force-storage`
: Override the storage location.

`--reuse-default-resource`
: Reuse the default resource.

## Validating Output Specs

Validate an outputs YAML file:

```bash
bfabric-app-runner validate outputs-spec outputs.yml
```

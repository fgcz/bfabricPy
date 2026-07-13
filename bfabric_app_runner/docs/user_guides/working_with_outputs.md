# Working with Outputs

This guide covers how to register processing results back into B-Fabric using bfabric-app-runner.

## Overview

After an app finishes processing, its output files and datasets need to be registered in B-Fabric. The output system supports three types of output specifications, defined in an `outputs.yml` file.

## Output YAML Format

Outputs are defined under a top-level `outputs:` key, whose value is a list of specifications:

```yaml
outputs:
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

Each type is shown below with a representative example. For the complete field reference, see the
[Output specification](../specs/output_specification.md).

### bfabric_copy_resource

Copies a local file to the B-Fabric storage and registers it as a resource.

```yaml
outputs:
  - type: bfabric_copy_resource
    local_path: results/output.mzML
    store_entry_path: output.mzML
    store_folder_path: /path/in/store
    update_existing: if_exists
    protocol: scp
```

### bfabric_dataset

Registers a local tabular file as a B-Fabric dataset.

```yaml
outputs:
  - type: bfabric_dataset
    local_path: results/summary.csv
    separator: ","
    name: "Experiment Results"
    has_header: true
    invalid_characters: remove
```

### bfabric_link

Creates a link resource in B-Fabric pointing to an external URL.

```yaml
outputs:
  - type: bfabric_link
    name: "Interactive Report"
    url: "https://example.com/report/456"
    update_existing: if_exists
```

## The `update_existing` field

`update_existing` controls what happens when an entry with the same identity already exists in B-Fabric;
its accepted values (`"no"`, `if_exists`, `required`) are documented on the
[Output specification](../specs/output_specification.md). Two things trip people up:

- In YAML, `"no"` **must be quoted** — bare `no` parses as the boolean `false` and fails validation.
- The YAML spec default is `if_exists`, but the `outputs register-single-file` CLI command's
  `--update-existing` flag defaults to `no`.

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

`--reuse-default-resource` / `--no-reuse-default-resource`
: Whether to reuse the workunit's auto-created default resource for the first copied file (default: enabled).

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
: UpdateExisting behavior (`no`, `if-exists`, or `required`; default `no`).

`--ssh-user`
: SSH user for remote transfers.

`--force-storage`
: Override the storage location.

`--reuse-default-resource` / `--no-reuse-default-resource`
: Whether to reuse the workunit's auto-created default resource (default: disabled for this command).

## Validating Output Specs

Validate an outputs YAML file:

```bash
bfabric-app-runner validate outputs-spec outputs.yml
```

# Output Specification

This guide covers defining outputs in `outputs.yml` to specify results that should be registered to B-Fabric.

## Overview

The output specification (`outputs.yml`) defines output files your application produces, including:

- Output types (resources, datasets, links)
- File paths and storage locations
- Update behavior for existing files
- Automatic association with workunits

## Output Specification Structure

```yaml
outputs:
  - type: <output_type>
    <type_specific_fields>
```

### Available Output Types

bfabric-app-runner supports multiple output types:

| Type | Target | Use Case |
| ---------------------- | ----------------------------------- | ----------------------------------------------------- |
| **bfabric_copy_resource** | B-Fabric resource file | Any result file to store |
| **bfabric_dataset** | B-Fabric dataset (tabular) | CSV/TSV results |
| **bfabric_link** | B-Fabric link to entity | URLs, external references |

## B-Fabric Copy Resource

Copy a local file to B-Fabric storage:

```yaml
outputs:
  - type: bfabric_copy_resource
    local_path: ./results/output.txt
    store_entry_path: WU${workunit.id}_output.txt
    store_folder_path: /optional/folder
    update_existing: "if_exists"
```

**Options:**

| Field | Type | Required | Description |
| -------------------- | ------------------------ | -------- | ------------------------------------------------------------------- |
| **type** | string | Yes | Must be `bfabric_copy_resource` |
| **local_path** | Path | Yes | Local path to file to copy |
| **store_entry_path** | Path | Yes | Target path in B-Fabric storage |
| **store_folder_path** | Path | No | Storage folder path (default: workunit rule) |
| **update_existing** | UpdateExisting enum | No | Behavior if file exists (default: `if_exists`) |

**Update Existing Options:**

| Value | Description |
| -------------- | ---------------------------------------------- |
| **no** | Fail if file exists |
| **if_exists** | Update existing file |
| **required** | File must exist (fail if missing) |

**Example:**

```yaml
outputs:
  - type: bfabric_copy_resource
    local_path: ./results/processed_data.csv
    store_entry_path: WU${workunit.id}_processed.csv
    update_existing: "if_exists"
```

## B-Fabric Dataset

Create a dataset from tabular data:

```yaml
outputs:
  - type: bfabric_dataset
    local_path: ./results/analysis.csv
    separator: ","
    name: "Analysis Results"
    has_header: true
    invalid_characters: ""
```

**Options:**

| Field | Type | Required | Description |
| -------------------- | ------- | -------- | ---------------------------------------------------- |
| **type** | string | Yes | Must be `bfabric_dataset` |
| **local_path** | Path | Yes | Local path to CSV/TSV file |
| **separator** | string | Yes | CSV separator (e.g., `,`, `\t`, `;`) |
| **name** | string | No | Dataset name (default: filename) |
| **has_header** | boolean | No | File has header row (default: `true`) |
| **invalid_characters** | string | No | Characters to filter from values (default: `""`) |

**Example:**

```yaml
outputs:
  # CSV dataset
  - type: bfabric_dataset
    local_path: ./results/proteins.csv
    separator: ","
    name: "Protein Identification Results"
    has_header: true

  # TSV dataset
  - type: bfabric_dataset
    local_path: ./results/genes.tsv
    separator: "\t"
    name: "Gene Expression Results"
    has_header: true
    invalid_characters: "\n\r"
```

## B-Fabric Link

Create a link to an entity or external URL:

```yaml
outputs:
  - type: bfabric_link
    name: "Results Dashboard"
    url: "https://dashboard.example.com/results/123"
    entity_type: "Workunit"
    entity_id: 12345
```

**Options:**

| Field | Type | Required | Description |
| ---------- | ------ | -------- | ---------------------------------------------- |
| **type** | string | Yes | Must be `bfabric_link` |
| **name** | string | Yes | Link name |
| **url** | string | Yes | Link URL |
| **entity_type** | string | No | Entity type to link (default: `Workunit`) |
| **entity_id** | integer | No | Entity ID (if linking to B-Fabric entity) |

**Example:**

```yaml
outputs:
  # External URL
  - type: bfabric_link
    name: "Results Dashboard"
    url: "https://dashboard.example.com/wu/123"

  # Link to workunit
  - type: bfabric_link
    name: "Previous Workunit"
    url: "https://fgcz-bfabric.uzh.ch/bfabric/workunit/100"
    entity_type: "Workunit"
    entity_id: 100
```

## Multiple Outputs

Define multiple outputs in a single file:

```yaml
outputs:
  # Main result file
  - type: bfabric_copy_resource
    local_path: ./results/processed_data.csv
    store_entry_path: WU${workunit.id}_results.csv

  # Summary statistics
  - type: bfabric_copy_resource
    local_path: ./results/summary.txt
    store_entry_path: WU${workunit.id}_summary.txt

  # Dataset for downstream analysis
  - type: bfabric_dataset
    local_path: ./results/for_downstream.csv
    separator: ","
    name: "Downstream Analysis"

  # External dashboard link
  - type: bfabric_link
    name: "Interactive Results"
    url: "https://dashboard.example.com/wu/${workunit.id}"
```

## Templating Workunit Variables

Output specifications support `${workunit.id}` variable:

```yaml
outputs:
  - type: bfabric_copy_resource
    local_path: ./results/output.txt
    store_entry_path: WU${workunit.id}_output.txt  # Dynamic filename
```

## Validating Output Specifications

Validate your output specification before using it:

```bash
bfabric-app-runner validate outputs-spec outputs.yml
```

Expected output:

```
OutputsSpec(
  outputs=[
    CopyResourceSpec(
      type='bfabric_copy_resource',
      local_path=PosixPath('./results/output.txt'),
      store_entry_path=PosixPath('WU12345_output.txt')
    ),
    SaveDatasetSpec(
      type='bfabric_dataset',
      local_path=PosixPath('./results/data.csv'),
      separator=',',
      name='Results',
      has_header=True
    ),
    SaveLinkSpec(
      type='bfabric_link',
      name='Dashboard',
      url='https://dashboard.com/wu/12345'
    )
  ]
)
```

## Registering Outputs

Register outputs to B-Fabric:

```bash
# Register all outputs from specification
bfabric-app-runner outputs register outputs.yml --workunit-id 12345

# Register a single file directly
bfabric-app-runner outputs register-single-file ./results/output.txt \
  --workunit-id 12345 \
  --store-entry-path WU12345_output.txt
```

See [Registering Outputs](./registering_outputs.md) for details.

## Best Practices

### Use Descriptive Filenames

```yaml
# Good: Descriptive filename
outputs:
  - type: bfabric_copy_resource
    store_entry_path: WU${workunit.id}_proteome_analysis.csv

# Avoid: Generic filename
outputs:
  - type: bfabric_copy_resource
    store_entry_path: WU${workunit.id}_output.csv
```

### Use Appropriate Output Types

```yaml
# Large binary files: Use resource
- type: bfabric_copy_resource
    local_path: ./results/data.tar.gz

# Tabular data: Use dataset
- type: bfabric_dataset
    local_path: ./results/table.csv
    separator: ","

# External references: Use link
- type: bfabric_link
    name: "Results Dashboard"
    url: "https://dashboard.com/wu/${workunit.id}"
```

### Handle Existing Files

```yaml
# Update existing file
- type: bfabric_copy_resource
    store_entry_path: WU${workunit.id}_results.csv
    update_existing: "if_exists"

# Fail if file shouldn't exist
- type: bfabric_copy_resource
    store_entry_path: WU${workunit.id}_unique.csv
    update_existing: "no"
```

### Clean Invalid Characters

```yaml
# For datasets, filter out newlines and special characters
- type: bfabric_dataset
    local_path: ./results/data.csv
    separator: ","
    invalid_characters: "\n\r\t"
```

### Group Related Outputs

```yaml
outputs:
  # Main analysis results
  - type: bfabric_copy_resource
    local_path: ./results/analysis.txt
    store_entry_path: WU${workunit.id}_analysis.txt

  # Summary statistics
  - type: bfabric_copy_resource
    local_path: ./results/summary.txt
    store_entry_path: WU${workunit.id}_summary.txt

  # Plots and figures
  - type: bfabric_copy_resource
    local_path: ./results/plots/
    store_entry_path: WU${workunit.id}_plots.tar.gz

  # Dataset for downstream
  - type: bfabric_dataset
    local_path: ./results/for_downstream.csv
    separator: ","
    name: "Downstream Dataset"
```

## Common Patterns

### Multiple Dataset Formats

```yaml
outputs:
  # CSV dataset
  - type: bfabric_dataset
    local_path: ./results/csv_output.csv
    separator: ","
    name: "CSV Results"

  # TSV dataset
  - type: bfabric_dataset
    local_path: ./results/tsv_output.tsv
    separator: "\t"
    name: "TSV Results"
```

### Versioned Outputs

```yaml
outputs:
  - type: bfabric_copy_resource
    local_path: ./results/v1.0_output.txt
    store_entry_path: WU${workunit.id}_v1.0.txt
    update_existing: "no"

  - type: bfabric_copy_resource
    local_path: ./results/v1.1_output.txt
    store_entry_path: WU${workunit.id}_v1.1.txt
    update_existing: "no"
```

### Conditional Registration

```bash
# Only register if file exists
if [ -f ./results/output.txt ]; then
  bfabric-app-runner outputs register outputs.yml --workunit-id 12345
fi
```

## Next Steps

- **[Registering Outputs](./registering_outputs.md)** - Registering outputs to B-Fabric
- **[Common Patterns](./common_patterns.md)** - Typical output scenarios
- **[Complete Workflow](../workflows/complete_workflow.md)** - End-to-end execution

## Related Documentation

- [Quick Start Tutorial](../../getting_started/quick_start.md) - Hands-on introduction
- [API Reference](../../api_reference/output_specification.md) - Complete output type documentation
- [Input Specification](../working_with_inputs/input_specification.md) - Defining input data

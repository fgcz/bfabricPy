# Workunits

The `bfabric-cli workunit` command provides operations for working with B-Fabric workunits (jobs and analysis pipelines).

## Overview

```bash
bfabric-cli workunit --help
```

Available subcommands:

| Subcommand | Purpose |
| ------------------- | --------------------------------------------------------------------------- |
| `not-available` | Check for workunits with missing results (commonly failed CompMS workunits) |
| `export-definition` | Export workunit definition to a YAML file |

______________________________________________________________________

## Checking for Pending Workunits

Find workunits that don't have results available, typically indicating failed or incomplete jobs.

### Basic Usage

```bash
bfabric-cli workunit not-available
```

### Parameters

No parameters required.

### Use Cases

The `not-available` command is commonly used to:

- **Find failed CompMS workunits**: Identify mass spectrometry jobs that didn't complete successfully
- **Monitor job status**: Check for workunits that need attention
- **Batch operations**: Find workunits for bulk reprocessing or investigation

### Example

```bash
# Check for pending workunits in TEST environment
BFABRICPY_CONFIG_ENV=TEST bfabric-cli workunit not-available

# Check in PRODUCTION (use with caution!)
BFABRICPY_CONFIG_ENV=PRODUCTION bfabric-cli workunit not-available
```

### Output

The output lists workunits that are in a "not available" state, typically showing:

- Workunit ID
- Associated application
- Status information
- Timestamps

### Caution

This command can return many results in production environments. Consider filtering or limiting the output for large deployments.

______________________________________________________________________

## Exporting Workunit Definitions

Export a workunit's definition to a YAML file for use with `bfabric-app-runner`.

### Basic Usage

```bash
bfabric-cli workunit export-definition [WORKUNIT_ID] [OPTIONS]
```

### Parameters

| Parameter | Required | Description |
| ------------- | -------- | ----------------------------------------------------- |
| `workunit_id` | Yes | ID of the workunit to export |
| `--file` | No | Output file path (default: `workunit_definition.yml`) |

### Examples

**Export to default filename:**

```bash
bfabric-cli workunit export-definition 316119
```

This creates `workunit_definition.yml` in the current directory.

**Export to custom filename:**

```bash
bfabric-cli workunit export-definition 316119 --file my_definition.yml
```

**Export with full path:**

```bash
bfabric-cli workunit export-definition 316119 --file /path/to/definitions/analysis_316119.yml
```

### Using the Exported Definition

**View the definition:**

```bash
cat workunit_definition.yml
```

**Parse in Python:**

```python
from bfabric.experimental.workunit_definition import WorkunitDefinition
from pathlib import Path
from rich.pretty import pprint

# Load and parse the definition
definition = WorkunitDefinition.from_yaml(Path("workunit_definition.yml"))
pprint(definition)
```

**Use with bfabric-app-runner:**

The exported YAML file can be used to run the same analysis:

```bash
bfabric-app-runner run workunit_definition.yml
```

______________________________________________________________________

## Finding Workunits

Use the generic API to find workunits:

### List Recent Workunits

```bash
bfabric-cli api read workunit --limit 20
```

### Filter by Status

```bash
# Find completed workunits
bfabric-cli api read workunit status FINISHED --limit 10

# Find running workunits
bfabric-cli api read workunit status RUNNING --limit 10
```

### Filter by Application

```bash
# Find workunits for a specific application
bfabric-cli api read workunit applicationid 123 --limit 10
```

### Filter by Container/Project

```bash
# Find workunits in a project
bfabric-cli api read workunit containerid 1234 --limit 20
```

### Filter by Date Range

```bash
# Find workunits created in a specific period
bfabric-cli api read workunit \
    createdafter 2024-01-01 \
    createdbefore 2024-02-01 \
    --columns id,created,description,status
```

### Show Workunit Details

```bash
# Show specific workunit details
bfabric-cli api read workunit id 12345
```

### Save Workunit List

```bash
# Save to file for further processing
bfabric-cli api read workunit --limit 100 --format json --file workunits.json
```

______________________________________________________________________

## Working with Workunit Resources

Workunits typically have associated resources (files, data, etc.).

### List Workunit Resources

```bash
# Find resources for a specific workunit
bfabric-cli api read resource workunitid 12345
```

### Show Workunit Datasets

```bash
# Find datasets for a workunit
bfabric-cli api read dataset workunitid 12345
```

______________________________________________________________________

## Workflow Examples

### Monitoring Failed CompMS Jobs

```bash
# 1. Find workunits with missing results (potential failures)
BFABRICPY_CONFIG_ENV=PRODUCTION bfabric-cli workunit not-available > failed_workunits.txt

# 2. Analyze the results
cat failed_workunits.txt

# 3. For each failed workunit, investigate
while read workunit_id; do
    bfabric-cli api read workunit id $workunit_id --format yaml
done < failed_workunits.txt
```

### Export and Reuse Workunit Definition

```bash
# 1. Find a successful workunit
bfabric-cli api read workunit status FINISHED --limit 10

# 2. Export its definition
bfabric-cli workunit export-definition 12345 --file my_analysis.yml

# 3. Customize the definition
vim my_analysis.yml

# 4. Run the analysis with bfabric-app-runner
bfabric-app-runner run my_analysis.yml
```

### Batch Processing Workunits

```bash
# 1. Get list of workunits to process
bfabric-cli api read workunit containerid 1234 --format json > workunits.json

# 2. Process with jq or other tools
cat workunits.json | jq -r '.[].id' | while read id; do
    # Export each definition
    bfabric-cli workunit export-definition $id --file workunit_$id.yml
done
```

______________________________________________________________________

## Tips and Best Practices

### Always Use Test Environment First

```bash
# Test queries on TEST environment
BFABRICPY_CONFIG_ENV=TEST bfabric-cli workunit not-available

# Verify results before running on PRODUCTION
```

### Export Before Deleting

Before re-running or deleting workunits, export their definitions:

```bash
# Export workunit definition for reference
bfabric-cli workunit export-definition 12345 --file backup_before_delete.yml
```

### Use Descriptive Filenames

```bash
# Use descriptive filenames for exported definitions
bfabric-cli workunit export-definition 12345 \
    --file compms_qc_pipeline_2025-01-20.yml
```

### Monitor Regularly

Set up regular monitoring for failed workunits:

```bash
# Create a script to check for pending workunits
#!/bin/bash
# monitor_workunits.sh
BFABRICPY_CONFIG_ENV=PRODUCTION bfabric-cli workunit not-available > pending_$(date +%Y%m%d).txt
```

______________________________________________________________________

## Common Issues

### Not-Available Returns Too Many Results

**Issue**: The command returns an overwhelming number of workunits

**Solutions**:

1. Filter by date range (requires using API instead)
2. Filter by application
3. Filter by container/project
4. Process results in batches

```bash
# Filter by date and application
bfabric-cli api read workunit \
    createdafter 2024-12-01 \
    applicationid 123 \
    --columns id,created,description
```

### Export Fails - Workunit Not Found

**Error**: Workunit with ID X not found

**Solution**: Verify the workunit exists:

```bash
bfabric-cli api read workunit id <workunit-id>
```

### Definition Parse Error

**Error**: Cannot parse exported definition

**Solutions**:

1. Verify the YAML syntax
2. Check for missing or corrupted fields
3. Ensure the workunit has all required components
4. Try exporting a different workunit to compare

______________________________________________________________________

## Integration with Other Tools

### bfabric-app-runner

Workunit definitions exported via the CLI are designed to work with `bfabric-app-runner`:

```bash
# Export a workunit
bfabric-cli workunit export-definition 12345 --file analysis.yml

# Run the analysis
bfabric-app-runner run analysis.yml

# Dry run (preview without execution)
bfabric-app-runner dry-run analysis.yml
```

### Python API

Workunit definitions can be loaded and manipulated in Python:

```python
from bfabric.experimental.workunit_definition import WorkunitDefinition
from pathlib import Path

# Load definition
definition = WorkunitDefinition.from_yaml(Path("workunit_definition.yml"))

# Access components
print(definition.parameters)
print(definition.executable)
print(definition.workunit)

# Modify and save
definition.description = "Modified description"
definition.to_yaml(Path("modified_definition.yml"))
```

______________________________________________________________________

## See Also

- [API Operations](api_operations.md) - Generic CRUD operations for finding workunits
- [Datasets](datasets) - Workunits often produce datasets
- [Executables](executables) - Executables used within workunits
- [Python Workunit API](../../api_reference/entity_types/workunit) - Using workunits in Python

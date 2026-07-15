# Workunits

The `bfabric-cli workunit` command provides operations for working with B-Fabric workunits (jobs and analysis pipelines).

## Overview

```bash
bfabric-cli workunit --help
```

Available subcommands:

| Subcommand | Purpose |
| ------------------- | --------------------------------------------------------------------------- |
| `upload` | Upload files to a workunit over tus (resumable) |
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

## Uploading Files

Upload files to a workunit over the [tus](https://tus.io/) resumable-upload protocol. This is the
modern replacement for the base64-over-SOAP `Bfabric.upload_resource` (which is limited to small
files): it streams in chunks, skips duplicates, and can resume an interrupted transfer.

### Prerequisites

The upload path requires the `tus` optional dependency and an **OAuth-backed** client whose token
carries the `tus` scope. Install the extra and authenticate once:

```bash
pip install 'bfabric[transfer]'
bfabric-cli auth login --scope "api:read api:write openid profile email groups tus"
```

### Basic Usage

```bash
bfabric-cli workunit upload FILE... --container-id <id> --application-id <id> [OPTIONS]
```

The pipeline is: compute checksums → check for duplicates → create the workunit and its resource
records → mint a short-lived tus token → transfer each file → mark the workunit `available`.

### Parameters

| Parameter | Required | Description |
| ---------------------- | -------- | ----------------------------------------------------------------------- |
| `FILE...` | Yes | Files and/or directories to upload (positional; directories recurse) |
| `--container-id` | \* | Container to create the workunit in |
| `--application-id` | \* | Application the workunit belongs to |
| `--workunit-id` | \* | Upload into this existing workunit instead of creating one |
| `--workunit-name` | No | Name for the created workunit (default "File upload") |
| `--force` | No | Skip the duplicate check and upload every file |
| `--track-job` | No | Create a `UPLOAD` job; the server flips it to DONE/FAILED |
| `--no-progress` | No | Disable the live progress bar (auto-off when stderr is not a terminal) |

\* Provide either `--workunit-id` (existing workunit) **or** both `--container-id` and
`--application-id` (new workunit); the two modes are mutually exclusive.

### Examples

**Upload files to a new workunit:**

```bash
bfabric-cli workunit upload results.txt report.pdf --container-id 40156 --application-id 447
```

**Upload a directory (recursed; relative paths are preserved as resource names):**

```bash
bfabric-cli workunit upload ./output_dir --container-id 40156 --application-id 447
```

Files identical to ones already in the container are skipped by MD5. Use `--force` to upload them
anyway.

**Upload into an existing workunit:**

```bash
bfabric-cli workunit upload extra.txt --workunit-id 336576
```

### Tracking the Upload as a Job

Pass `--track-job` to attach a B-Fabric *job* to the transfer:

```bash
bfabric-cli workunit upload big.raw --container-id 40156 --application-id 447 --track-job
```

A *job* is a B-Fabric entity that records a unit of tracked work. B-Fabric creates jobs around
scenarios like launching a web application or uploading a file. Each job carries an **action** that
says what kind of work it represents, and a **status** that moves from `NEW` to `DONE` or `FAILED`.

B-Fabric only *stores* the action and status — it does not act on them itself. It is the service
interfacing with B-Fabric that reads the action and drives the status. Here that service is the tus
upload server: `--track-job` creates a job of action `UPLOAD` parented to the workunit and hands its
id to the tus token, and the tus server (not B-Fabric) then flips the job from `NEW` to `DONE` (or
`FAILED`) once the files finish transferring. A service that doesn't handle a job's action leaves it
alone.

Without `--track-job` the files still upload; you just don't get a job object recording the outcome.

### Resuming an Interrupted Upload

A tus transfer is resumable: if a connection drops mid-transfer, the server retains the bytes it
already received. From Python you capture the upload URL (via `on_url`) and pass it back as
`resume_url` to pick up where you left off instead of re-sending everything. A runnable end-to-end
proof against a live server -- abort mid-flight, wait, resume -- lives at
`bfabric/src/bfabric/examples/prove_tus_resume.py`:

```bash
python -m bfabric.examples.prove_tus_resume --config-env DEMO --container-id 403 --application-id 435
```

### Using the Python API

The CLI wraps `bfabric.operations.workunit.upload_files`, which you can drive directly -- useful when
you want to feed progress into your own pipeline runner:

```python
from pathlib import Path

from bfabric import Bfabric
from bfabric.operations.workunit import UploadFilesParams, upload_files

client = Bfabric.connect()  # OAuth-backed client with the 'tus' scope
summary = upload_files(
    client,
    files=[Path("results.txt"), Path("output_dir")],
    params=UploadFilesParams(container_id=40156, application_id=447, track_job=True),
    on_progress=lambda name, done, total: print(f"{name}: {done}/{total}"),
)
print(
    f"Workunit {summary.workunit_id}: uploaded {summary.uploaded}, skipped {summary.skipped}"
)
```

A file whose transfer fails is recorded in `summary.failures` rather than raising; setup failures
(bad auth, missing scope, resource-creation errors) raise `BfabricTransferError`, and the workunit is
flipped to `failed` (never deleted) so the partial state stays diagnosable.

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
- [Python Workunit API](../../api_reference/entity_types/index) - Using workunits in Python

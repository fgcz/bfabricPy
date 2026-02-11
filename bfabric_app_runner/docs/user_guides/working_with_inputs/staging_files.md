# Staging Input Files

This guide covers downloading and preparing input files using the bfabric-app-runner inputs commands.

## Overview

Input staging is the process of preparing input files for your application. bfabric-app-runner provides:

- Automatic downloading from B-Fabric
- Local file copying from filesystem or SSH
- Static file generation from embedded content
- Integrity checking (checksums)
- Smart caching (only re-download if changed)
- Filtered preparation (prepare specific inputs)

## Input Staging Workflow

```
Define inputs (inputs.yml) → Validate → List → Prepare → Use in app
```

## Available Commands

### 1. List Inputs

View what inputs will be prepared:

```bash
bfabric-app-runner inputs list inputs.yml [target_folder]
```

**Parameters:**

| Parameter | Type | Required | Description |
| --------------- | ---------- | -------- | ---------------------------------------------- |
| **inputs_yaml** | Path | Yes | Path to inputs.yml file |
| **target_folder** | Path | No | Target folder for input files (default: current) |

**Example:**

```bash
# List inputs in current directory
bfabric-app-runner inputs list inputs.yml

# List inputs in specific folder
bfabric-app-runner inputs list inputs.yml /path/to/work_dir
```

**Output:**

```
InputsSpec(
  inputs=[
    FileState(
      spec=FileSpec(...),
      file=Path('input.txt'),
      exists=True,
      integrity=IntegrityState.Correct
    ),
    DatasetSpec(...),
    ...
  ]
)
```

### 2. Check Inputs

Verify input files are present and have correct content:

```bash
bfabric-app-runner inputs check inputs.yml [target_folder]
```

**Parameters:**

Same as `list` command.

**Behavior:**

- Downloads missing files (if applicable)
- Verifies checksums (for B-Fabric resources)
- Exits with error if files are incorrect
- Useful for CI/CD pipelines

**Example:**

```bash
# Check inputs in current directory
bfabric-app-runner inputs check inputs.yml
```

**Output:**

```
All input files are correct.
```

Or if incorrect:

```
Encountered invalid input states: {IntegrityState.ChecksumMismatch}
```

### 3. Prepare Inputs

Download and prepare all input files:

```bash
bfabric-app-runner inputs prepare inputs.yml [target_folder] [options]
```

**Parameters:**

| Parameter | Type | Required | Description |
| --------------- | ---------- | -------- | ---------------------------------------------- |
| **inputs_yaml** | Path | Yes | Path to inputs.yml file |
| **target_folder** | Path | No | Target folder for input files (default: current) |
| **--ssh-user** | string | No | SSH user for downloading files |
| **--filter** | string | No | Only prepare this input file |

**Example:**

```bash
# Prepare all inputs in current directory
bfabric-app-runner inputs prepare inputs.yml

# Prepare in specific folder
bfabric-app-runner inputs prepare inputs.yml /path/to/work_dir

# Prepare with custom SSH user
bfabric-app-runner inputs prepare inputs.yml --ssh-user myuser

# Prepare only specific input file
bfabric-app-runner inputs prepare inputs.yml --filter data.csv
```

### 4. Clean Inputs

Remove local copies of input files:

```bash
bfabric-app-runner inputs clean inputs.yml [target_folder] [options]
```

**Parameters:**

Same as `prepare` command, except no `--filter` option.

**Example:**

```bash
# Clean all input files
bfabric-app-runner inputs clean inputs.yml

# Clean in specific folder
bfabric-app-runner inputs clean inputs.yml /path/to/work_dir

# Clean with custom SSH user
bfabric-app-runner inputs clean inputs.yml --ssh-user myuser
```

## File States and Integrity

bfabric-app-runner tracks file state and integrity:

| State | Description |
| ------------------------ | ---------------------------------------------------- |
| **FileState.Exists** | File exists in target folder |
| **IntegrityState.Correct** | File exists and matches checksum (if applicable) |
| **IntegrityState.Missing** | File is missing |
| **IntegrityState.ChecksumMismatch** | File exists but has wrong checksum |

**List Output Example:**

```
Inputs:

1. sample_data.csv (bfabric_dataset)
   ✓ File exists: /work/inputs/sample_data.csv
   ✓ Integrity: Correct

2. reference.fasta (bfabric_resource)
   ✓ File exists: /work/inputs/reference.fasta
   ✓ Integrity: Correct

3. config.json (static_file)
   ✓ File exists: /work/inputs/config.json
   - No integrity check (static file)
```

## Caching Behavior

bfabric-app-runner implements smart caching:

### Downloaded Files (B-Fabric)

- Downloads only if file is missing
- Re-downloads if checksum mismatches
- Skips download if file exists and is correct

### Local Files

- Copies only if file is missing
- Skips copy if file exists (regardless of checksum)

### Static Files

- Writes content only if file is missing
- Overwrites if file exists

## Filtering Inputs

Prepare only specific input files:

```bash
# Prepare only the dataset input
bfabric-app-runner inputs prepare inputs.yml --filter sample_data.csv

# Prepare only resource inputs (matching pattern)
bfabric-app-runner inputs prepare inputs.yml --filter reference
```

```{note}
Filter matches against the `filename` field in input specifications.
```

## Using in Makefiles

When using `bfabric-app-runner prepare workunit`, a Makefile is generated with input staging targets:

```makefile
# Prepare all inputs
inputs:
    bfabric-app-runner inputs prepare inputs.yml $(CURDIR)/inputs

# Prepare specific input
inputs-filtered:
    bfabric-app-runner inputs prepare inputs.yml $(CURDIR)/inputs --filter data.csv

# Check inputs
inputs-check:
    bfabric-app-runner inputs check inputs.yml $(CURDIR)/inputs

# Clean inputs
inputs-clean:
    bfabric-app-runner inputs clean inputs.yml $(CURDIR)/inputs
```

## SSH User Configuration

Some inputs require SSH access for file operations:

```yaml
# Resource that requires SSH access
inputs:
  - type: file
    source:
      ssh:
        host: "data.server.com"
        path: "/data/reference.fasta"
    filename: reference.fasta
```

Specify SSH user for download:

```bash
bfabric-app-runner inputs prepare inputs.yml --ssh-user myuser
```

```{note}
If no SSH user is specified, bfabric-app-runner uses the current system user.
```

## Common Workflows

### Development Workflow

```bash
# 1. Define inputs (inputs.yml)
# 2. Validate inputs
bfabric-app-runner validate inputs-spec inputs.yml

# 3. List what will be prepared
bfabric-app-runner inputs list inputs.yml .

# 4. Prepare inputs
bfabric-app-runner inputs prepare inputs.yml .

# 5. Run application
make process
```

### CI/CD Pipeline

```bash
# In CI/CD pipeline
bfabric-app-runner inputs check inputs.yml .
if [ $? -eq 0 ]; then
    bfabric-app-runner inputs prepare inputs.yml .
    bfabric-app-runner run workunit app_spec.yml /scratch/workdir 12345
else
    echo "Input validation failed"
    exit 1
fi
```

### Incremental Development

```bash
# Prepare only changed inputs
bfabric-app-runner inputs prepare inputs.yml --filter new_dataset.csv

# Check specific input
bfabric-app-runner inputs check inputs.yml . | grep new_dataset
```

## Troubleshooting

### File Not Downloading

**Issue:** Input file not being downloaded

**Solution:**

```bash
# Check if file exists in B-Fabric
bfabric-cli api read resource id 12345

# Verify ID is correct
# Check permissions
```

### Checksum Mismatch

**Issue:** `IntegrityState.ChecksumMismatch`

**Solution:**

```bash
# Clean and re-download
bfabric-app-runner inputs clean inputs.yml .
bfabric-app-runner inputs prepare inputs.yml .
```

### SSH Connection Issues

**Issue:** Cannot download from SSH source

**Solution:**

```bash
# Test SSH connection
ssh user@host.example.com "ls /data"

# Specify correct SSH user
bfabric-app-runner inputs prepare inputs.yml --ssh-user myuser
```

### Filter Not Working

**Issue:** Filter doesn't match expected input

**Solution:**

```bash
# List inputs to see filenames
bfabric-app-runner inputs list inputs.yml .

# Use exact filename from list
bfabric-app-runner inputs prepare inputs.yml --filter "exact_filename.csv"
```

## Best Practices

### Always Validate Before Use

```bash
bfabric-app-runner validate inputs-spec inputs.yml
bfabric-app-runner inputs check inputs.yml .
bfabric-app-runner inputs prepare inputs.yml .
```

### Use Descriptive Filenames

```yaml
# Good: Descriptive
inputs:
  - type: bfabric_resource
    filename: reference_genome_hg38.fasta
    id: 12345

# Avoid: Generic
inputs:
  - type: bfabric_resource
    filename: reference.fasta
    id: 12345
```

### Enable Checksum Verification

```yaml
# For critical inputs
inputs:
  - type: bfabric_resource
    check_checksum: true  # Default, but be explicit for critical data
    filename: reference_genome.fasta
    id: 12345
```

### Group Related Inputs

```yaml
inputs:
  # Main data
  - type: bfabric_dataset
    filename: proteomics_data.csv
    id: 12345

  # Reference data
  - type: bfabric_resource
    filename: reference_genome.fasta
    id: 67890

  # Configuration
  - type: static_file
    filename: params.json
    content: "threads: 4"
```

## Next Steps

- **[B-Fabric Datasets](./bfabric_datasets.md)** - Working with dataset inputs
- **[B-Fabric Resources](./bfabric_resources.md)** - Working with resource inputs
- **[Static Files](./static_files.md)** - Working with static files
- **[Input Specification](./input_specification.md)** - Defining input specifications

## Related Documentation

- [Quick Start Tutorial](../../getting_started/quick_start.md) - Hands-on introduction
- [Input Specification](./input_specification.md) - Defining input types
- [Complete Workflow](../workflows/complete_workflow.md) - End-to-end workflow example
- [API Reference](../../api_reference/input_specification.md) - Complete input type documentation

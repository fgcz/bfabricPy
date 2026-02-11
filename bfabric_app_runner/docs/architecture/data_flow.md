# Data Flow

This document explains how data flows through bfabric-app-runner from workunit definition to output registration.

## Overview

The data flow in bfabric-app-runner follows a linear pipeline:

```
Workunit Definition → Dispatch → Input Staging → Processing → Output Registration → Collect → Workunit Status Update
```

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│ B-Fabric                                                      │
│ (Workunits, Datasets, Resources)                                   │
└──────────────┬─────────────────────────────────────┬──────────────────┘
               │                                     │
               ▼                                     │
      ┌─────────────────────────┐                    │
      │ Workunit Definition    │                    │
      │                      │                    │
      │ 1. Load from B-Fabric│                    │
      │                      │                    │
      │ 2. Parse YAML (optional)│                    │
      │                      │                    │
      └──────────────┬───────────────┘                    │
                   │                                   │
                   ▼                                   │
        ┌──────────────────────────────────────────────┐        │
        │ bfabric-app-runner                  │        │
        │                                    │        │
        │ Phase 1: Dispatch                  │        │
        │ • Load app spec                    │        │
        │ • Load workunit definition          │        │
        │ • Generate workflow parameters        │        │
        │ • Create chunk directories (if any)  │        │
        │                                    │        │
        └──────────────┬──────────────────────┘        │
                     │                             │
                     ▼                             │
        ┌──────────────────────────────────────────────────────────┐
        │ Input Staging (Phase 2)                      │        │
        │                                                │        │
        │ • Download B-Fabric datasets                  │        │
        │ • Download B-Fabric resources                 │        │
        │ • Copy local files                         │        │
        │ • Generate static files                      │        │
        │ • Verify checksums (for resources)          │        │
        │ • Skip re-downloads (caching)               │        │
        │                                                │        │
        └──────────────┬──────────────────────────────────────┘        │
                     │                             │
                     ▼                             │
        ┌──────────────────────────────────────────────────────────┐
        │ Processing (Phase 3)                           │        │
        │                                                │        │
        │ • Read staged input files                  │        │
        │ • Execute app logic (exec/Docker/Python)  │        │
        │ • Generate output files                    │        │
        │ • Handle multiple chunks (if applicable)       │        │
        │                                                │        │
        └──────────────┬──────────────────────────────────────┘        │
                     │                             │
                     ▼                             │
        ┌──────────────────────────────────────────────────────────┐
        │ Output Registration (Phase 4)                 │        │
        │                                                │        │
        │ • Copy resource files to B-Fabric storage (SCP)   │        │
        │ • Create datasets from tabular data           │        │
        │ • Create entity links                       │        │
        │ • Associate with workunit                    │        │
        │                                                │        │
        └──────────────┬──────────────────────────────────────┘        │
                     │                             │
                     ▼                             │
        ┌──────────────────────────────────────────────────────────┐
        │ Collection (Phase 5)                             │        │
        │                                                │        │
        │ • Finalize workflow                            │        │
        │ • Clean temporary files                      │        │
        │ • Generate reports                          │        │
        │ • Finalize workunit status                  │        │
        │                                                │        │
        └──────────────┬──────────────────────────────────────┘        │
                     │                             │
                     ▼                             │
      ┌─────────────────────────────────────────────────────────┐
      │ B-Fabric                                   │
      │ (Updated Status, Registered Outputs)            │
      └─────────────────────────────────────────────────────────┘
```

## Detailed Flow

### Step 1: Workunit Definition

**Source:** B-Fabric workunit entity or local YAML file

**Process:**

1. **Load workunit entity:**

   - Query B-Fabric for workunit by ID
   - Extract: application ID, name, storage information
   - Extract: execution parameters

2. **Or load from YAML:**

   - Parse local workunit_definition.yml
   - Extract: execution and registration information

3. **Output:** WorkunitDefinition object containing:

   - `execution`: Raw parameters for the app
   - `registration`: B-Fabric metadata for registration

**Data Types:**

- **Execution params:** Key-value strings (e.g., `param1: "value1"`)
- **Dataset ID:** Integer (for dataset-flow applications)
- **Resource IDs:** List of integers (for resource-flow applications)

### Step 2: Dispatch Phase

**Input:** WorkunitDefinition

**Process:**

1. **Load app specification:**

   - Read `app_spec.yml`
   - Resolve app version using app_id and app_name
   - Expand Mako templates (`${app.id}`, `${app.name}`, `${app.version}`)

2. **Generate workflow parameters:**

   - Execute dispatch command
   - Create `workflow_params.json` or similar
   - Generate chunk configuration (if applicable)

3. **Create directory structure:**

   - Create `inputs/`, `outputs/`, `chunks/` directories
   - Write `app_env.yml` with environment configuration

**Output:** Prepared workunit directory ready for input staging

**Generated Files:**

- `app_env.yml`: Environment configuration
- `workunit_definition.yml`: Workunit details
- Chunk directories: `chunk1/`, `chunk2/`, etc. (if applicable)

### Step 3: Input Staging

**Input:** inputs.yml specification

**Process:**

1. **Parse input specification:**

   - Read `inputs.yml`
   - Validate Pydantic models
   - Resolve input types

2. **For each input type:**

   **B-Fabric Datasets:**

   - Query B-Fabric for dataset by ID
   - Download dataset file
   - Save to `inputs/<filename>`

   **B-Fabric Resources:**

   - Query B-Fabric for resource by ID
   - Download resource file
   - Verify checksum (optional)
   - Save to `inputs/<filename>`

   **Local Files:**

   - Copy from source path
   - Save to `inputs/<filename>`

   **Static Files:**

   - Generate from embedded content
   - Write to `inputs/<filename>`

3. **Caching:**

   - Check if file exists in `inputs/`
   - Compare modification time
   - Skip download if unchanged
   - Download only if missing or checksum mismatched

**Output:** All input files in `inputs/` directory

**State Tracking:**

- `Exists`: File is present
- `Integrity.Correct`: File matches checksum (if applicable)
- `Integrity.Missing`: File not found
- `Integrity.ChecksumMismatch`: File exists but wrong checksum

### Step 4: Processing

**Input:** Staged input files, app specification, chunk directory

**Process:**

1. **Read input files:**

   - Load files from `inputs/` or `chunks/<chunk>/inputs/`
   - For chunked workflows: Each chunk has its own `inputs/`

2. **Execute app command:**

   - Based on command type:
     - **exec**: Run command on host using `shlex.split()`
     - **docker**: Run container with mounts, environment variables
     - **python_env**: Run in uv-managed virtual environment
   - Pass chunk directory as context

3. **Generate output files:**

   - Write results to `outputs/` or `chunks/<chunk>/outputs/`
   - Create CSV files, logs, reports, etc.

**Output:** Generated output files in `outputs/` directory

**Context Variables:**

- For each chunk: `$chunk_dir` resolves to the chunk's directory
- Process command receives `chunk_dir` as current directory

### Step 5: Output Registration

**Input:** outputs.yml specification, output files, workunit definition

**Process:**

1. **Parse output specification:**

   - Read `outputs.yml`
   - Validate Pydantic models
   - Resolve output types

2. **For each output type:**

   **B-Fabric Copy Resource:**

   - Read local file from `<local_path>`
   - SCP to B-Fabric storage
   - Use `<store_entry_path>` as filename
   - Use workunit's storage directory (if no `store_folder_path` specified)

   **B-Fabric Dataset:**

   - Read CSV/TSV file from `<local_path>`
   - Parse according to `<separator>` and `<has_header>`
   - Create dataset in B-Fabric
   - Associate with workunit

   **B-Fabric Link:**

   - Create entity link with `<name>` and `<url>`
   - Associate with workunit and entity (if specified)

3. **Workunit Association:**

   - Link outputs to workunit
   - Use workunit's storage for resource files
   - Use workunit ID for entity links

**Output:** Registered entities in B-Fabric

**Templating:**

- `${workunit.id}`: Workunit ID for dynamic filenames
- `${chunk.id}`: Chunk ID (for chunked workflows)

### Step 6: Collection

**Input:** Workunit definition, completed outputs

**Process:**

1. **Execute collect command:**

   - Run `collect` command from app spec
   - Finalize workflow results
   - Clean up temporary files
   - Generate summary reports

2. **Update workunit status:**

   - If successful: Set to "available"
   - If failed: Set to "failed"
   - Return exit code accordingly

**Output:** Finalized workunit state

**Clean Up Tasks:**

- Remove temporary files
- Compress large outputs
- Generate final reports
- Archive logs

## Parallel Processing (Chunking)

For large datasets, the data flow splits into parallel chunks:

```
┌─────────────────────────────────────────────────────────────┐
│ Input Staging                                       │
│                                                  │
│ inputs/                                          │
│ • dataset.csv (all data)                           │
│ • reference.fasta (reference data)                  │
└──────────────┬─────────────────────────────────────┘
               │
               ▼
        ┌──────────────────────────────────────────┐
        │ Dispatch Phase                   │
        │                                  │
        │ • Create chunk1/, chunk2/, chunk3/  │
        │ • Copy input specs to each chunk     │
        │                                  │
        └──────────────┬─────────────────────────────┘
                     │
                     │
                     ▼
        ┌────────────────────────────────────────────────────────────────┐
        │ Parallel Processing (3 chunks)                       │
        │                                                │
        │ chunk1/inputs/ → process → outputs → collect       │
        │ chunk2/inputs/ → process → outputs → collect       │
        │ chunk3/inputs/ → process → outputs → collect       │
        │                                                │
        └──────────────┬─────────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────────────┐
        │ Output Registration                               │
        │                                                │
        │ • Register chunk1 outputs                        │
        │ • Register chunk2 outputs                        │
        │ • Register chunk3 outputs                        │
        │                                                │
        └─────────────────────────────────────────────────────┘
```

**Chunking Benefits:**

- **Parallel execution**: Process multiple chunks simultaneously
- **Fault tolerance**: One chunk failure doesn't stop others
- **Resource optimization**: Better cluster utilization
- **SLURM arrays**: Submit as job arrays

## Error Handling and Recovery

### Input Staging Failures

**Scenario:** B-Fabric download fails

**Handling:**

- Retry logic with exponential backoff
- Report failure to user
- Mark file state as `Missing`

**Recovery:**

- Re-run `inputs` command
- Use cached successful downloads
- Continue with remaining inputs

### Processing Failures

**Scenario:** App command fails

**Handling:**

- Exit with error code
- Log error details
- Preserve partial outputs if any

**Recovery:**

- Fix error (e.g., update app spec)
- Re-run `process` command
- Use existing inputs (no re-download)

### Output Registration Failures

**Scenario:** SCP to B-Fabric fails

**Handling:**

- Retry with exponential backoff
- Report detailed error messages
- Mark workunit status as "failed"

**Recovery:**

- Fix SSH/network issues
- Re-run `outputs` command
- Continue with remaining outputs

## Data Integrity

### Checksum Verification

**Purpose:** Ensure B-Fabric resources haven't changed

**Process:**

1. **Download initial checksum:** Query resource, get checksum
2. **Download file:** Get resource file content
3. **Calculate local checksum:** Compute SHA256 of downloaded file
4. **Compare:** Match against B-Fabric checksum
5. **Action:**
   - Match: Use cached file
   - Mismatch: Re-download, update cache

**Supported Types:**

- B-Fabric resources
- B-Fabric resource archives
- B-Fabric resource datasets

### File State Tracking

bfabric-app-runner tracks file state throughout the flow:

| State | When Set | Implication |
| -------------- | ------------------------------------- | -------------------------------------- |
| **Missing** | Initial state / After failed download | File must be downloaded |
| **Correct** | After successful download/verification | File is ready to use |
| **Mismatched** | After checksum verification | File needs to be re-downloaded |

## Best Practices

### Atomic Operations

Each phase performs atomic operations:

- **Input staging**: All files present or all failed
- **Processing**: All outputs complete or none
- **Output registration**: All outputs registered or all failed

### Idempotent Operations

Re-running any command should be safe:

- **Inputs command**: Skip already-cached files
- **Outputs command**: Handle `update_existing` option correctly
- **Status updates**: Only update when state changes

### Caching Strategy

Implement smart caching:

```python
# Example logic
if file.exists() and checksum_matches():
    skip_download()  # Use cached file
else:
    download_file()  # Get fresh file
```

### Error Propagation

Fail fast to preserve context:

```python
# Example: Input download fails
try:
    download_all_inputs()
except DownloadError as e:
    # Report immediately, don't continue
    raise  # Stop workflow

# Good: Allows early intervention
```

## Related Documentation

- **[Input Specification Guide](../user_guides/working_with_inputs/input_specification.md)** - Defining input data
- **[Output Specification Guide](../user_guides/working_with_outputs/output_specification.md)** - Defining output data
- **[Staging Files](../user_guides/working_with_inputs/staging_files.md)** - Input staging operations
- **[Registering Outputs](../user_guides/working_with_outputs/registering_outputs.md)** - Output registration operations
- **[Architecture Overview](./overview.md)** - High-level architecture
- **[Execution Model](./execution_model.md)** - Execution environment details

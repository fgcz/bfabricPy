# Complete Workflow

This guide demonstrates a complete end-to-end workflow using bfabric-app-runner, from defining specifications to running in production.

## Overview

A complete bfabric-app-runner workflow includes these stages:

```
1. Define specifications (app_spec.yml, inputs.yml, outputs.yml)
2. Validate specifications
3. Prepare workunit
4. Run workflow phases (dispatch → inputs → process → outputs → collect)
5. Register outputs
6. Update workunit status
```

## Workflow Example

Let's walk through a complete proteomics data processing pipeline.

### Step 1: Create App Specification

Create `app_spec.yml`:

```yaml
# app_spec.yml

bfabric:
  app_runner: "1.0.0"
  workflow_template_step_id: 100

versions:
  - version: "1.0.0"
    commands:
      # Prepare workflow configuration
      dispatch:
        type: "exec"
        command: "python generate_config.py"
        env:
          WORKFLOW_VERSION: "1.0.0"

      # Process data in Docker container
      process:
        type: "docker"
        image: "proteomics-processor:1.0.0"
        command: "/app/process.py --config /app/config/workflow_params.json"
        env:
          APP_VERSION: "${app.version}"
          NUM_WORKERS: "4"
        mounts:
          read_only:
            - ["./inputs", "/app/data"]
            - ["/opt/reference_genome", "/app/reference"]
          writeable:
            - ["./outputs", "/app/results"]
          share_bfabric_config: true

      # Finalize and clean up
      collect:
        type: "exec"
        command: "python finalize_results.py"
```

### Step 2: Create Input Specification

Create `inputs.yml`:

```yaml
# inputs.yml

inputs:
  # Raw data from B-Fabric dataset
  - type: bfabric_dataset
    id: 53706
    filename: raw_proteomics_data.csv
    separator: ","

  # Reference genome from B-Fabric resource
  - type: bfabric_resource
    id: 2700958
    filename: reference_genome.fasta
    check_checksum: true

  # Static configuration file
  - type: static_file
    content: |
      version: 1.0.0
      database: swissprot
      fdr_threshold: 0.01
      min_peptide_length: 7
    filename: search_params.txt
```

### Step 3: Create Output Specification

Create `outputs.yml`:

```yaml
# outputs.yml

outputs:
  # Main results file
  - type: bfabric_copy_resource
    local_path: ./results/identified_proteins.csv
    store_entry_path: WU${workunit.id}_proteins.csv
    update_existing: "if_exists"

  # Summary statistics
  - type: bfabric_copy_resource
    local_path: ./results/summary_statistics.txt
    store_entry_path: WU${workunit.id}_summary.txt

  # Dataset for downstream analysis
  - type: bfabric_dataset
    local_path: ./results/downstream_ready.csv
    separator: ","
    name: "Downstream Analysis Ready"
    has_header: true
```

### Step 4: Validate Specifications

Validate all YAML files before use:

```bash
# Validate app specification
bfabric-app-runner validate app-spec app_spec.yml --app-id 100 --app-name "ProteomicsProcessor"

# Validate input specification
bfabric-app-runner validate inputs-spec inputs.yml

# Validate output specification
bfabric-app-runner validate outputs-spec outputs.yml
```

Expected output for each:

```
✓ App specification is valid
✓ Inputs specification is valid
✓ Outputs specification is valid
```

### Step 5: Local Development and Testing

Prepare a workunit for local development:

```bash
# Prepare workunit directory
bfabric-app-runner prepare workunit \
  --app-spec app_spec.yml \
  --work-dir /tmp/proteomics_dev \
  --workunit-ref 12345 \
  --read-only
```

This creates a structured directory:

```
/tmp/proteomics_dev/
├── Makefile                # Generated Makefile with all commands
├── app_spec.yml           # Your app specification
├── workunit_definition.yml # Workunit details
├── inputs.yml             # Your input specification
├── outputs.yml            # Your output specification
├── app_env.yml            # Environment configuration
├── inputs/                # Input files will be staged here
└── outputs/               # Outputs will be placed here
```

Navigate to the workunit directory and explore available commands:

```bash
cd /tmp/proteomics_dev
make help
```

Test individual phases:

```bash
# Stage input files
make inputs

# Execute processing
make process

# Register outputs (skipped in read-only mode)
# make outputs

# Run complete workflow
make run-all
```

### Step 6: Production Execution

For production, use the end-to-end `run workunit` command:

```bash
bfabric-app-runner run workunit \
  /path/to/app_spec.yml \
  /scratch/bfabric/proteomics \
  12345
```

Parameters:

| Parameter | Type | Description |
| --------------- | --------- | --------------------------------------------------------- |
| **app_spec** | Path | Path to app_spec.yml |
| **scratch_root** | Path | Root directory for workunit folders |
| **workunit_ref** | int/Path | Workunit ID or path to workunit YAML definition |

This command:

1. Loads workunit definition from B-Fabric
2. Prepares workunit directory structure
3. Updates workunit status to "processing"
4. Executes: `dispatch → inputs → process → outputs → collect`
5. Updates workunit status to "available" or "failed"

## Workflow Phases in Detail

### Phase 1: Dispatch

**Purpose:** Prepare workflow parameters and context

**What happens:**

- Executes `dispatch` command from app_spec.yml
- Generates configuration files
- Sets up environment
- Creates chunk directories (if applicable)

**Example output:**

```
=== Dispatch ===
Generating workflow configuration...
Created: /scratch/workunit/config/workflow_params.json
Created: /scratch/workunit/inputs/
Created: /scratch/workunit/chunks/chunk1/
```

### Phase 2: Inputs

**Purpose:** Prepare input files

**What happens:**

- Downloads B-Fabric datasets
- Downloads B-Fabric resources (with checksum verification)
- Copies local files
- Generates static files

**Example output:**

```
=== Inputs ===
Preparing input files...
✓ Downloaded: dataset#53706 → inputs/raw_proteomics_data.csv
✓ Downloaded: resource#2700958 → inputs/reference_genome.fasta
✓ Generated: inputs/search_params.txt (static file)
All input files prepared.
```

### Phase 3: Process

**Purpose:** Execute main application logic

**What happens:**

- Runs `process` command from app_spec.yml
- In Docker, shell, or Python environment
- For each chunk (if chunking is enabled)
- Generates output files

**Example output:**

```
=== Process ===
Starting Docker container...
Processing data...
✓ Identified 1,234 proteins
✓ Generated summary statistics
Processing complete.
```

### Phase 4: Outputs

**Purpose:** Register results to B-Fabric

**What happens:**

- Copies resource files to B-Fabric storage
- Creates datasets from tabular data
- Creates links to external resources
- Associates outputs with workunit

**Example output:**

```
=== Outputs ===
Registering outputs...
✓ Registered: WU12345_proteins.csv (resource#2789001)
✓ Registered: WU12345_summary.txt (resource#2789002)
✓ Created: Downstream Analysis Ready (dataset#123457)
All outputs registered.
```

### Phase 5: Collect

**Purpose:** Post-processing and cleanup

**What happens:**

- Executes `collect` command from app_spec.yml
- Finalizes results
- Cleans up temporary files
- Generates reports

**Example output:**

```
=== Collect ===
Finalizing workflow...
✓ Generated final report
✓ Cleaned temporary files
Workflow complete.
```

## Workunit Status Updates

bfabric-app-runner automatically updates workunit status:

| Status | When Set | Description |
| --------------- | -------------------------------------- | ----------------------------------- |
| **processing** | At start of workflow | Workunit is being processed |
| **available** | On successful completion | Results are ready |
| **failed** | On error or failure | Workunit failed |

## Advanced: Chunked Workflows

For large datasets, you can use chunking to process data in parallel:

```yaml
# app_spec.yml
versions:
  - version: "1.0.0"
    commands:
      dispatch:
        type: "exec"
        command: "python split_data.py --chunks 4"
```

This creates multiple chunk directories:

```
scratch/workunit/
├── inputs.yml
├── inputs/
├── outputs/
└── chunks/
    ├── chunk1/
    │   ├── inputs.yml
    │   ├── inputs/
    │   └── outputs/
    ├── chunk2/
    │   ├── inputs.yml
    │   ├── inputs/
    │   └── outputs/
    ├── chunk3/
    └── chunk4/
```

Run specific chunk:

```bash
make process chunk=chunk1
make outputs chunk=chunk1
```

Run all chunks:

```bash
make run-all  # Processes all chunks in parallel (if SLURM)
```

## Error Handling

### Dispatch Fails

```bash
# Check workunit definition
cat workunit_definition.yml

# Re-run dispatch
make dispatch
```

### Process Fails

```bash
# Check logs (Docker, application logs)
ls -la ./logs/

# Re-run process
make process
```

### Outputs Registration Fails

```bash
# Check output files exist
ls -la ./outputs/

# Validate outputs.yml
bfabric-app-runner validate outputs-spec ../outputs.yml

# Re-run outputs registration
make outputs
```

## CI/CD Integration

For automated pipelines:

```yaml
# .github/workflows/process.yml

name: Process Workunit

on:
  workflow_dispatch:
    inputs:
      workunit_id:
        required: true
        type: number

jobs:
  process:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install bfabric-app-runner
        run: uv tool install bfabric_app_runner

      - name: Process workunit
        run: |
          bfabric-app-runner run workunit \
            ./app_spec.yml \
            /tmp/workdir \
            ${{ github.event.inputs.workunit_id }}
```

## Best Practices

### Always Validate Specifications

```bash
bfabric-app-runner validate app-spec app_spec.yml
bfabric-app-runner validate inputs-spec inputs.yml
bfabric-app-runner validate outputs-spec outputs.yml
```

### Test Locally First

```bash
# Use --read-only for safe local testing
bfabric-app-runner prepare workunit \
  --app-spec app_spec.yml \
  --work-dir /tmp/test_workunit \
  --workunit-ref 12345 \
  --read-only

# Run through Makefile
make run-all

# Verify outputs
ls -la ./outputs/
```

### Use Meaningful Filenames

```yaml
outputs:
  - type: bfabric_copy_resource
    store_entry_path: WU${workunit.id}_proteins_identified_v1.0.csv
```

### Implement Error Handling

```yaml
collect:
  type: "exec"
  command: "python finalize.py || echo 'Processing failed'"
```

### Monitor Workunit Status

```bash
# Check workunit status
bfabric-cli api read workunit id 12345

# Watch for status changes
watch -n 5 'bfabric-cli api read workunit id 12345'
```

## Next Steps

- **[Testing Locally](./testing_locally.md)** - Development and testing workflows
- **[Docker Environment](../execution/docker_environment.md)** - Docker configuration
- **[Production Deployment](./production_deployment.md)** - Production best practices
- **[CLI Reference](../cli_reference/running_apps.md)** - Production commands

## Related Documentation

- [Quick Start Tutorial](../../getting_started/quick_start.md) - Hands-on introduction
- [App Specification](../creating_an_app/app_specification.md) - App configuration
- [Input Specification](../working_with_inputs/input_specification.md) - Input types
- [Output Specification](../working_with_outputs/output_specification.md) - Output types
- [Staging Files](../working_with_inputs/staging_files.md) - Preparing inputs

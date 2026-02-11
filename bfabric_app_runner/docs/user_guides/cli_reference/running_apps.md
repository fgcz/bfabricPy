# Running Apps

This guide covers the production commands for running bfabric-app-runner applications end-to-end.

## Overview

bfabric-app-runner provides two main approaches for running applications:

| Approach | Command | Use Case |
| --------- | -------- | -------------------------------------------- |
| **Prepare + Make** | `bfabric-app-runner prepare workunit` | Development and testing (local execution) |
| **Run End-to-End** | `bfabric-app-runner run workunit` | Production execution (automated) |

## Command: Prepare Workunit

Prepare a workunit directory structure for local development and testing:

```bash
bfabric-app-runner prepare workunit \
  --app-spec <app_spec.yml> \
  --work-dir <work_dir> \
  --workunit-ref <workunit_ref> \
  [options]
```

### Parameters

| Parameter | Type | Required | Description |
| --------------- | ---------- | -------- | ------------------------------------------------------------ |
| **--app-spec** | Path | Yes | Path to app_spec.yml file |
| **--work-dir** | Path | Yes | Directory where workunit will be executed |
| **--workunit-ref** | int/Path | Yes | Workunit ID or path to workunit YAML definition |
| **--ssh-user** | string | No | SSH user for file operations |
| **--force-storage** | Path | No | Override storage path (for testing) |
| **--force-app-version** | string | No | Override app version (for testing) |
| **--read-only** | boolean | No | Prevent writes to B-Fabric (for testing) |
| **--use-external-runner** | boolean | No | Use external bfabric-app-runner from PATH |

### What It Does

The `prepare workunit` command:

1. **Loads workunit definition** from B-Fabric (ID) or local YAML
2. **Resolves app specification** with app ID and name
3. **Creates directory structure:**
   ```
   <work_dir>/
   ├── Makefile                # Generated Makefile with all targets
   ├── app_spec.yml           # App specification
   ├── workunit_definition.yml # Workunit details
   ├── app_env.yml            # Environment configuration
   ├── inputs.yml             # Input specification
   └── outputs.yml            # Output specification
   ```
4. **Does NOT execute** the workflow (unless using Makefile manually)

### Examples

**Basic Preparation:**

```bash
bfabric-app-runner prepare workunit \
  --app-spec ./app_spec.yml \
  --work-dir /tmp/my_workunit \
  --workunit-ref 12345
```

**With Custom SSH User:**

```bash
bfabric-app-runner prepare workunit \
  --app-spec ./app_spec.yml \
  --work-dir /tmp/my_workunit \
  --workunit-ref 12345 \
  --ssh-user myuser
```

**Read-Only Mode (Testing):**

```bash
# Safe for local testing (no B-Fabric writes)
bfabric-app-runner prepare workunit \
  --app-spec ./app_spec.yml \
  --work-dir /tmp/test_workunit \
  --workunit-ref 12345 \
  --read-only
```

**Override App Version (Testing):**

```bash
# Test with specific version
bfabric-app-runner prepare workunit \
  --app-spec ./app_spec.yml \
  --work-dir /tmp/test_workunit \
  --workunit-ref 12345 \
  --force-app-version "1.1.0"
```

## Command: Run Workunit

Execute a workunit end-to-end in production:

```bash
bfabric-app-runner run workunit \
  <app_spec.yml> \
  <scratch_root> \
  <workunit_ref>
```

### Parameters

| Parameter | Type | Required | Description |
| ------------- | ------ | -------- | ---------------------------------------------------- |
| **app_spec** | Path | Yes | Path to app_spec.yml file |
| **scratch_root** | Path | Yes | Root directory for workunit folders |
| **workunit_ref** | int/Path | Yes | Workunit ID or path to workunit YAML definition |

### What It Does

The `run workunit` command:

1. **Loads workunit definition** from B-Fabric
2. **Prepares workunit directory** (same as prepare command)
3. **Updates workunit status** to "processing"
4. **Executes complete workflow:**
   - dispatch
   - inputs
   - process (for each chunk)
   - outputs (for each chunk)
   - collect
5. **Updates workunit status** to "available" or "failed"
6. **Creates output directory:** `<scratch_root>/A{app_id}_{app_name}/WU{workunit_id}`

### Directory Structure Created

```
<scratch_root>/
└── A100_MyApp/
    └── WU12345/
        ├── Makefile
        ├── app_spec.yml
        ├── workunit_definition.yml
        ├── app_env.yml
        ├── inputs.yml
        ├── outputs.yml
        ├── inputs/           # Staged input files
        ├── outputs/          # Generated output files
        └── chunks/           # If chunking (chunk1/, chunk2/, etc.)
```

### Examples

**Basic Execution:**

```bash
bfabric-app-runner run workunit \
  ./app_spec.yml \
  /scratch/bfabric \
  12345
```

**With Workunit YAML File:**

```bash
# Use local workunit definition instead of ID
bfabric-app-runner run workunit \
  ./app_spec.yml \
  /scratch/bfabric \
  ./workunit_definitions/my_workunit.yml
```

**Custom Scratch Root:**

```bash
# Use custom location for workunit files
bfabric-app-runner run workunit \
  ./app_spec.yml \
  /custom/scratch/location \
  12345
```

## Workflow Execution Details

### Status Updates

The `run workunit` command automatically manages workunit status:

| Status | When Set | B-Fabric Status |
| ---------- | ------------------------------ | ----------------------- |
| **processing** | At start of workflow | Workunit is running |
| **available** | On successful completion | Results are ready |
| **failed** | On error or failure | Workunit failed |

### Chunked Workflows

If workunit uses chunking:

```
Workflow for Workunit #12345 (4 chunks):

1. Dispatch (setup)
2. Process chunk1 → Process chunk2 → Process chunk3 → Process chunk4
3. Outputs chunk1 → Outputs chunk2 → Outputs chunk3 → Outputs chunk4
4. Collect
```

### Error Handling

If any phase fails:

1. Workunit status set to "failed"
2. Workflow stops immediately
3. Error details logged
4. No partial results registered

## Using the Generated Makefile

After running `prepare workunit`, you can use the generated Makefile for manual execution:

```bash
cd <work_dir>

# See all available commands
make help

# Run complete workflow
make run-all

# Run individual phases
make dispatch    # Prepare workflow
make inputs      # Stage input files
make process     # Execute application
make outputs     # Register results
make collect     # Finalize and cleanup
```

## Common Use Cases

### Development Workflow

```bash
# 1. Prepare workunit for development
bfabric-app-runner prepare workunit \
  --app-spec ./app_spec.yml \
  --work-dir /tmp/dev_workunit \
  --workunit-ref 12345 \
  --read-only

# 2. Navigate to workunit directory
cd /tmp/dev_workunit

# 3. Run workflow phases manually
make inputs
make process
make outputs

# 4. Check results
ls -la ./outputs/
```

### Production Workflow

```bash
# End-to-end execution with automatic status management
bfabric-app-runner run workunit \
  ./app_spec.yml \
  /scratch/production \
  12345
```

### Testing with Specific Version

```bash
# Test with different app version
bfabric-app-runner prepare workunit \
  --app-spec ./app_spec.yml \
  --work-dir /tmp/test_v1.1.0 \
  --workunit-ref 12345 \
  --force-app-version "1.1.0" \
  --read-only

cd /tmp/test_v1.1.0
make run-all
```

### Multiple Workunits

```bash
# Process multiple workunits in sequence
for workunit_id in 12345 12346 12347; do
  bfabric-app-runner run workunit \
    ./app_spec.yml \
    /scratch/bfabric \
    $workunit_id
done
```

## Troubleshooting

### Workunit Not Found

**Issue:** `Workunit #12345 not found`

**Solution:**

```bash
# Verify workunit exists
bfabric-cli api read workunit id 12345

# Check correct ID
bfabric-cli api read workunit name "My Workunit"
```

### App Version Not Found

**Issue:** `App version 1.0.0 not found in specification`

**Solution:**

```bash
# List available versions
bfabric-app-runner validate app-spec ./app_spec.yml

# Check version string
grep "version:" app_spec.yml
```

### Permission Denied

**Issue:** Cannot write to scratch directory

**Solution:**

```bash
# Check scratch directory permissions
ls -la /scratch/bfabric

# Fix permissions
chmod 755 /scratch/bfabric
```

### Workflow Fails Mid-Execution

**Issue:** Workflow stops halfway through

**Solution:**

```bash
# Check workunit status
bfabric-cli api read workunit id 12345

# Review logs in workunit directory
ls -la <work_dir>/logs/

# Re-run with same parameters
bfabric-app-runner run workunit ./app_spec.yml /scratch/bfabric 12345
```

## Best Practices

### Always Use Prepare for Development

```bash
# Use --read-only to prevent accidental B-Fabric writes
bfabric-app-runner prepare workunit \
  --app-spec ./app_spec.yml \
  --work-dir /tmp/dev \
  --workunit-ref 12345 \
  --read-only
```

### Use Run for Production

```bash
# Automated execution with proper status management
bfabric-app-runner run workunit ./app_spec.yml /scratch/prod 12345
```

### Monitor Workunit Status

```bash
# After run, verify status
bfabric-cli api read workunit id 12345

# Watch for status changes
watch -n 10 'bfabric-cli api read workunit id 12345'
```

### Use Descriptive Scratch Roots

```bash
# Organize workunits by project
/scratch/projects/proteomics/WU12345/
/scratch/projects/genomics/WU12346/
/scratch/projects/metabolomics/WU12347/
```

### Validate Before Running

```bash
# Validate all specifications
bfabric-app-runner validate app-spec app_spec.yml --app-id 100 --app-name "MyApp"
bfabric-app-runner validate inputs-spec inputs.yml
bfabric-app-runner validate outputs-spec outputs.yml
```

## Next Steps

- **[Testing Locally](../workflows/testing_locally.md)** - Development and testing workflows
- **[Complete Workflow](../workflows/complete_workflow.md)** - End-to-end workflow details
- **[Developer Tools](./developer_tools.md)** - Validation and testing commands

## Related Documentation

- [Quick Start Tutorial](../../getting_started/quick_start.md) - Hands-on introduction
- [Prepare Command](./developer_tools.md#prepare-workunit) - Detailed prepare command
- [Complete Workflow](../workflows/complete_workflow.md) - Full workflow example
- [Developer Tools](./developer_tools.md) - All CLI commands

# Quick Start

This 10-minute tutorial will guide you through creating and running your first bfabric-app-runner application.

## Prerequisites

Before starting, ensure you have:

1. ✅ **Installed bfabric-app-runner**: Follow the [Installation Guide](installation.md)
2. ✅ **Configured B-Fabric credentials**: Follow the [Configuration Guide](configuration.md)
3. ✅ **Access to B-Fabric test instance** (recommended for first try)

## What You'll Build

You'll create a simple application that:

1. **Fetches input data** from a B-Fabric dataset
2. **Processes the data** using a shell command
3. **Registers the output** back to B-Fabric

This is a typical workflow for many bioinformatics applications.

______________________________________________________________________

## Step 1: Create an App Specification

Create a file named `app_spec.yml`:

```yaml
versions:
  - version: "1.0.0"
    commands:
      dispatch:
        type: "exec"
        command: "echo 'Preparing inputs...' > workflow_params.json"

      process:
        type: "exec"
        command: "cat workflow_params.json"

      collect:
        type: "exec"
        command: "echo 'Completed!'"
```

**What this does:**

- **dispatch**: Creates a simple `workflow_params.json` file
- **process**: Displays the workflow parameters
- **collect**: Marks the workflow as complete

## Step 2: Create an Input Specification

Create a file named `inputs.yml`:

```yaml
inputs:
  - type: bfabric_dataset
    id: 53706
    filename: sample_data.csv
```

**What this does:**

- Downloads a B-Fabric dataset (ID: 53706)
- Saves it as `sample_data.csv`

```{note}
Replace `53706` with a dataset ID from your B-Fabric instance. Use `bfabric-cli api read dataset --limit 5` to find available datasets.
```

## Step 3: Create an Output Specification

Create a file named `outputs.yml`:

```yaml
outputs:
  - type: bfabric_copy_resource
    local_path: workflow_params.json
    store_entry_path: WU${workunit.id}_params.json
```

**What this does:**

- Registers `workflow_params.json` as a B-Fabric resource
- Uses the workunit ID in the filename (via `${workunit.id}`)

______________________________________________________________________

## Step 4: Validate Your Specifications

Before running, validate your YAML files:

```bash
# Validate app specification
bfabric-app-runner validate app-spec app_spec.yml

# Validate inputs specification
bfabric-app-runner validate inputs-spec inputs.yml

# Validate outputs specification
bfabric-app-runner validate outputs-spec outputs.yml
```

You should see output like:

```
✓ App specification is valid
✓ Inputs specification is valid
✓ Outputs specification is valid
```

## Step 5: Test Input Staging

Test that your inputs can be prepared:

```bash
# Create a test directory
mkdir -p /tmp/test_run && cd /tmp/test_run

# List what will be downloaded
bfabric-app-runner inputs list ../inputs.yml .

# Prepare (download) the input files
bfabric-app-runner inputs prepare ../inputs.yml .
```

Expected output:

```
InputsSpec(
  inputs=[
    DatasetSpec(type='bfabric_dataset', id=53706, filename='sample_data.csv', separator=',')
  ]
)
```

You should now see `sample_data.csv` in your directory.

```bash
ls -la
```

______________________________________________________________________

## Step 6: Prepare a Workunit (Test Locally)

For local development and testing, prepare a workunit directory:

```bash
bfabric-app-runner prepare workunit \
  --app-spec ../app_spec.yml \
  --work-dir /tmp/my_workunit \
  --workunit-ref 12345
```

```{note}
Replace `12345` with a real workunit ID from B-Fabric, or use a test workunit ID for initial testing.
```

This creates a structured workunit directory with:

```
/tmp/my_workunit/
├── Makefile                # Generated Makefile with all commands
├── app_spec.yml           # Your app specification
├── inputs/                # Downloaded input files
│   └── sample_data.csv
└── outputs/               # Where outputs will be registered
```

## Step 7: Run the Workflow

Navigate to the workunit directory and explore the available commands:

```bash
cd /tmp/my_workunit
make help
```

You'll see all available commands:

```
Available targets:
  dispatch    - Prepare and stage input files
  inputs      - Prepare input files
  process     - Execute the main application logic
  outputs     - Register output files to B-Fabric
  collect     - Post-processing and cleanup
  run-all     - Run the complete workflow (dispatch → inputs → process → outputs → collect)
```

Now run the complete workflow:

```bash
make run-all
```

Expected output:

```
=== Dispatch ===
Preparing inputs...

=== Inputs ===
✓ Input files prepared

=== Process ===
Preparing inputs...

=== Outputs ===
✓ Output files registered

=== Collect ===
Completed!
```

## Step 8: Run End-to-End (Production)

For production use, you can run a workunit end-to-end with a single command:

```bash
bfabric-app-runner run workunit \
  /path/to/app_spec.yml \
  /scratch/bfabric \
  12345
```

Parameters:

- **app_spec.yml**: Path to your app specification
- **/scratch/bfabric**: Scratch directory for workunit files
- **12345**: Workunit ID or path to workunit YAML definition

This command:

1. Loads the workunit definition from B-Fabric
2. Prepares the workunit directory
3. Executes the complete workflow
4. Updates workunit status (processing → available/failed)

______________________________________________________________________

## What Just Happened?

Let's break down what we did:

### App Specification (`app_spec.yml`)

Defines **how your app works**:

- **Version**: "1.0.0" (for versioning)
- **Commands**: What happens in each phase
  - `dispatch`: Prepare the workflow
  - `process`: Execute the main logic
  - `collect`: Clean up and finalize

### Input Specification (`inputs.yml`)

Defines **what data you need**:

- Downloads datasets from B-Fabric
- Validates files before use
- Caches files to avoid re-downloading

### Output Specification (`outputs.yml`)

Defines **what you produce**:

- Registers results back to B-Fabric
- Can create resources or datasets
- Automatic workunit association

### Workflow Execution

The **workflow phases**:

| Phase | Purpose |
| ---------- | --------------------------------------- |
| **dispatch** | Prepare workflow parameters and context |
| **inputs** | Download and stage input files |
| **process** | Execute the main application logic |
| **outputs** | Register output files to B-Fabric |
| **collect** | Post-processing and cleanup |

______________________________________________________________________

## Next Steps

Now that you've completed your first workflow, explore more:

| Want to... | Read this guide |
| --------------------------------------- | ----------------------------------------------------- |
| Create a real bioinformatics app | [Creating an App](../user_guides/creating_an_app/) |
| Work with Docker containers | [Docker Environment](../user_guides/execution/docker_environment.md) |
| Handle multiple input types | [Working with Inputs](../user_guides/working_with_inputs/) |
| Register complex outputs | [Working with Outputs](../user_guides/working_with_outputs/) |
| Use SLURM for job scheduling | [SLURM Integration](../user_guides/execution/slurm_integration.md) |
| Learn CLI commands in detail | [CLI Reference](../user_guides/cli_reference/) |

## Common Questions

### Where can I find dataset IDs?

```bash
# List recent datasets
bfabric-cli api read dataset --limit 10

# Search datasets by name
bfabric-cli api read dataset name "my_dataset"
```

### Can I run without B-Fabric?

Yes! For testing, you can use static files:

```yaml
inputs:
  - type: file
    path: ./local_file.csv
    filename: data.csv
```

### How do I add Docker?

Replace the `process` command with Docker:

```yaml
process:
  type: "docker"
  image: "myapp:1.0.0"
  command: "/app/run.sh"
  mounts:
    read_only:
      - ["./inputs", "/app/data"]
    writeable:
      - ["./outputs", "/app/output"]
```

See [Docker Environment](../user_guides/execution/docker_environment.md) for details.

## Troubleshooting

### Authentication Failed

```
Error: Authentication failed
```

**Solution**: Check your `~/.bfabricpy.yml` configuration:

```bash
# Test connection
bfabric-cli api read workunit --limit 1
```

### Input File Not Found

```
Error: Dataset 12345 not found
```

**Solution**: Verify the dataset ID exists in your B-Fabric instance:

```bash
bfabric-cli api read dataset id 12345
```

### Make Command Not Found

```
make: command not found
```

**Solution**: Install `make`:

```bash
# macOS
xcode-select --install

# Ubuntu/Debian
sudo apt-get install build-essential

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
```

## Related Documentation

- [Installation Guide](installation.md) - Installation options and troubleshooting
- [Configuration Guide](configuration.md) - Setting up B-Fabric credentials
- [Creating an App](../user_guides/creating_an_app/) - Comprehensive app development guide
- [User Guides](../user_guides/index.md) - More tutorials and examples

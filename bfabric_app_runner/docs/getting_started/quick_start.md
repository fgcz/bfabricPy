# Quick Start

This tutorial walks through running a B-Fabric application workunit using bfabric-app-runner. There are two workflows: the **Makefile workflow** for interactive development and debugging, and the **run workunit** command for unattended execution.

## Prerequisites

1. **bfabric-app-runner installed**: Follow [Installation Guide](installation.md)
2. **B-Fabric credentials configured**: `~/.bfabricpy.yml` must contain valid credentials
3. **A workunit to process**: You need a workunit ID from B-Fabric

______________________________________________________________________

## Makefile Workflow (Interactive)

The Makefile workflow is the recommended approach for development and debugging. It breaks execution into discrete steps that you can run, inspect, and re-run individually.

### Step 1: Prepare the Working Directory

```bash
bfabric-app-runner prepare workunit <app_spec> <work_dir> <workunit_ref>
```

For example:

```bash
bfabric-app-runner prepare workunit /path/to/app.yml ./work 12345
```

This creates a working directory containing a `Makefile` and configuration files. The `<workunit_ref>` is the workunit ID from B-Fabric.

Optional flags:

- `--ssh-user <user>` -- SSH user for remote file transfers
- `--force-storage <storage_id>` -- Override the default storage
- `--force-app-version <version>` -- Override the app version (useful for testing a `devel` version)
- `--read-only` -- Prepare in read-only mode

### Step 2: Explore Available Targets

```bash
cd work && make help
```

This prints all available Makefile targets and their descriptions.

### Step 3: Run Each Stage

Execute the stages in order:

```bash
make dispatch
```

Dispatches the workunit: loads information from B-Fabric, determines which resources are needed, and generates `inputs.yml` files for each chunk.

```bash
make inputs
```

Downloads the required input files based on `inputs.yml`.

```bash
make process
```

Runs the actual processing (e.g., a Snakemake pipeline or other computation).

```bash
make stage
```

Uploads results back to B-Fabric.

______________________________________________________________________

## Run Workunit (Unattended)

For automated execution (e.g., from a Slurm script), use `run workunit` to execute all stages in sequence:

```bash
bfabric-app-runner run workunit <app_definition> <scratch_root> <workunit_ref>
```

This runs dispatch, inputs, process, and outputs in a single invocation.

______________________________________________________________________

## Running Individual Actions

You can also run individual stages using the `action` subcommands, which is useful when re-running a specific stage after a failure:

```bash
bfabric-app-runner action dispatch <work_dir>
bfabric-app-runner action inputs <work_dir>
bfabric-app-runner action process <work_dir>
bfabric-app-runner action outputs <work_dir>
```

Or run all stages at once:

```bash
bfabric-app-runner action run-all <work_dir>
```

______________________________________________________________________

## Troubleshooting

### A step temporarily failed

Re-run the failing stage. For example, if `make process` failed:

```bash
make process
```

Or run all remaining stages:

```bash
make run-all
```

The Makefile targets are idempotent where possible.

### You need to edit an intermediate result

Edit the relevant file in the working directory and re-run the stage:

```bash
# Edit as needed, then re-run
make process
```

Sometimes you may need to delete generated files before re-running.

### The app needs major changes

For significant changes, use a development version of the app:

1. Set up a `devel` version in your `app.yml` pointing to your local source code (see [Configuration Guide](configuration.md))
2. Re-prepare the workunit with the development version:

```bash
bfabric-app-runner prepare workunit /path/to/app.yml ./work 12345 --force-app-version devel
```

______________________________________________________________________

## Next Steps

- [Configuration Guide](configuration.md) -- Learn how to write and customize `app.yml`
- [Installation Guide](installation.md) -- Other installation options

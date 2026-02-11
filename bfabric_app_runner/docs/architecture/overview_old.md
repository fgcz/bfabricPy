# Architecture

High-level architecture documentation for bfabric-app-runner.

```{toctree}
:maxdepth: 1
overview
data_flow
execution_model
```

## Overview

bfabric-app-runner is a declarative workflow system for executing bioinformatics applications on B-Fabric workunits. It provides:

- **Declarative specifications** - Define apps, inputs, and outputs in YAML
- **Multiple execution environments** - Docker, shell, Python virtual environments
- **Automated workflow management** - Dispatch → inputs → process → outputs → collect
- **B-Fabric integration** - Automatic input staging and output registration
- **SLURM support** - Job scheduling for production deployments
- **Workunit management** - Complete lifecycle handling (processing → available/failed)

## Key Concepts

### App Specification (`app_spec.yml`)

Defines application structure and execution commands:

```yaml
bfabric:
  app_runner: "1.0.0"

versions:
  - version: "1.0.0"
    commands:
      dispatch: ...  # Prepare workflow
      process: ...   # Execute application
      collect: ...   # Finalize results
```

**Purpose:** Centralize app configuration, support multiple versions, define execution strategy.

**Related:** [App Specification Guide](../user_guides/creating_an_app/app_specification.md)

### Input Specification (`inputs.yml`)

Defines input data required by the application:

```yaml
inputs:
  - type: bfabric_dataset
    id: 12345
    filename: data.csv
  - type: bfabric_resource
    id: 67890
    filename: reference.fasta
```

**Purpose:** Declaratively specify input sources (B-Fabric datasets/resources, local files, static content).

**Related:** [Input Specification Guide](../user_guides/working_with_inputs/input_specification.md)

### Output Specification (`outputs.yml`)

Defines results to register to B-Fabric:

```yaml
outputs:
  - type: bfabric_copy_resource
    local_path: ./results/output.txt
    store_entry_path: WU${workunit.id}_output.txt
  - type: bfabric_dataset
    local_path: ./results/data.csv
    separator: ","
```

**Purpose:** Declaratively specify output registration (resources, datasets, links).

**Related:** [Output Specification Guide](../user_guides/working_with_outputs/output_specification.md)

### Workunit Definition

B-Fabric entity representing a work unit to be executed:

```yaml
execution:
  dataset: 12345                    # Input dataset ID
  raw_parameters:
    param1: "value1"
    param2: "value2"

registration:
  application_id: 100
  application_name: "MyApp"
  workunit_id: 200
  workunit_name: "Processing Job"
  container_id: 300
  container_type: "project"
  storage_id: 400
  storage_output_folder: "results"
```

**Purpose:** Separate execution parameters from registration information for flexibility and caching.

**Related:** [Workunit Definition Guide](../../bfabric/docs/advanced_topics/workunit_definitions/index.md)

## Workflow Phases

A complete bfabric-app-runner workflow executes these phases in order:

```
1. Dispatch → 2. Inputs → 3. Process → 4. Outputs → 5. Collect
```

### Phase 1: Dispatch

**Purpose:** Prepare workflow context and generate configuration

**Actions:**

- Load workunit definition
- Resolve app specification
- Execute dispatch command
- Generate workflow parameters
- Create chunk directories (if applicable)

**Context:** `workunit_ref`, `work_dir`

**Output:** Configuration files, parameter files, chunk structure

### Phase 2: Inputs

**Purpose:** Stage input files for processing

**Actions:**

- Download B-Fabric datasets
- Download B-Fabric resources (with checksum verification)
- Copy local files
- Generate static files
- Cache downloads (skip if unchanged)

**Context:** `work_dir`, `inputs.yml`

**Output:** All input files in `inputs/` directory

### Phase 3: Process

**Purpose:** Execute main application logic

**Actions:**

- Run command (exec, shell, Docker, Python environment)
- For each chunk (if chunking enabled)
- Generate output files

**Context:** `chunk_dir`

**Output:** Results in `outputs/` directory

### Phase 4: Outputs

**Purpose:** Register results to B-Fabric

**Actions:**

- Register resource files (via SCP)
- Create datasets from tabular data
- Create entity links

**Context:** `workunit_ref`, `outputs.yml`, output files

**Output:** Registered entities in B-Fabric

### Phase 5: Collect

**Purpose:** Finalize workflow and clean up

**Actions:**

- Execute collect command
- Clean temporary files
- Generate reports
- Finalize workunit status

**Context:** `workunit_ref`, `chunk_dir`

**Output:** Clean state, reports

## Execution Models

bfabric-app-runner supports multiple execution models:

| Model | Description | Use Case |
| ---------- | -------------------------------------------- | ----------------------------------- |
| **Direct** | Simple command execution on host | Simple scripts, quick jobs |
| **Docker** | Containerized execution | Isolated environments, reproducibility |
| **Python Env**| Virtual environments with uv | Python applications, dependency management |
| **SLURM** | Batch job scheduling | Production HPC clusters |

### Direct Execution

Commands execute directly on the host system:

```yaml
commands:
  process:
    type: "exec"
    command: "python3 process.py"
```

**Characteristics:**

- Simple and fast
- No isolation overhead
- Uses host dependencies
- Good for development and testing

### Docker Execution

Commands execute in Docker containers:

```yaml
commands:
  process:
    type: "docker"
    image: "myapp:1.0.0"
    command: "/app/process.py"
    mounts:
      read_only:
        - ["./inputs", "/app/data"]
      writeable:
        - ["./outputs", "/app/results"]
```

**Characteristics:**

- Full isolation from host
- Reproducible environments
- Easy deployment across environments
- Can limit resources (CPU, memory, disk)

### Python Virtual Environment

Commands execute in uv-managed Python environments:

```yaml
commands:
  process:
    type: "python_env"
    pylock: "./requirements.lock"
    command: "python process.py"
```

**Characteristics:**

- Isolated Python dependencies
- Reproducible with lock files
- Can add local extra dependencies
- Good for Python applications

### SLURM Batch Execution

Workunits can be submitted as SLURM jobs:

```bash
bfabric-app-runner run workunit \
  ./app_spec.yml \
  /scratch/bfabric \
  12345
```

This submits a SLURM job that:

- Allocates resources (CPUs, memory)
- Runs the complete workflow
- Logs output to SLURM
- Updates workunit status

## Data Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                                                              │
│  B-Fabric                                               │
│  (datasets, resources, workunits)                            │
│                                                              │
└───────────────────────┬───────────────────────────────────────────┘
                       │
                       │ Stage (download)
                       │
                       ▼
         ┌─────────────────────────────────────┐
         │ bfabric-app-runner                   │
         │                                    │
         │  1. Dispatch: Prepare workflow       │
         │  2. Inputs: Stage data             │
         │  3. Process: Execute application      │
         │  4. Outputs: Register results       │
         │  5. Collect: Finalize             │
         │                                    │
         └──────────────┬────────────────────────┘
                      │
                      │ Register (SCP/upload)
                      │
                      ▼
         ┌─────────────────────────────────────┐
         │ B-Fabric Storage                   │
         │  (output resources, datasets)          │
         │                                    │
         └─────────────────────────────────────────┘
```

**Data Flow:**

1. **Input Stage:** Workunit definition from B-Fabric → bfabric-app-runner
2. **Dispatch:** Generate workflow parameters and context
3. **Inputs Stage:** B-Fabric datasets/resources → bfabric-app-runner → local files
4. **Process:** App reads local files, generates outputs
5. **Outputs Stage:** bfabric-app-runner → B-Fabric storage (resources, datasets)
6. **Collect:** Finalize workflow and update workunit status

## Directory Structure

### Prepared Workunit Directory

```
<work_dir>/
├── Makefile                  # Generated Makefile with all targets
├── app_spec.yml             # App specification
├── workunit_definition.yml # Workunit details
├── app_env.yml              # Environment configuration
├── inputs.yml               # Input specification
├── outputs.yml              # Output specification
├── inputs/                  # Staged input files
├── outputs/                 # Generated output files
└── chunks/                  # Subdirectories (if chunking)
    ├── chunk1/
    │   ├── inputs/
    │   └── outputs/
    ├── chunk2/
    └── ...
```

### Scratch Root Structure

```
<scratch_root>/
└── A{app_id}_{app_name}/
    └── WU{workunit_id}/
        ├── Makefile
        ├── app_spec.yml
        ├── workunit_definition.yml
        ├── app_env.yml
        ├── inputs/
        ├── outputs/
        └── chunks/
```

## Components

### Action System

The action system (`bfabric-app-runner action`) executes individual workflow phases:

- **`action run-all`** - Execute complete workflow (all phases)
- **`action dispatch`** - Prepare workflow context
- **`action inputs`** - Stage input files
- **`action process`** - Execute application logic
- **`action outputs`** - Register output files
- **`action collect`** - Finalize workflow

### Input Resolution System

The input resolution system transforms specifications into file operations:

- **Specification parsing** - Read and validate inputs.yml
- **Type-specific handlers** - Different logic for datasets, resources, files
- **Integrity checking** - Verify checksums for B-Fabric resources
- **Caching** - Skip re-downloads if files are unchanged
- **File generation** - Create static files from embedded content

### Output Registration System

The output registration system registers results to B-Fabric:

- **Specification parsing** - Read and validate outputs.yml
- **Resource copying** - SCP files to B-Fabric storage
- **Dataset creation** - Parse CSV/TSV files and create datasets
- **Entity linking** - Create B-Fabric entity links
- **Workunit association** - Link outputs to workunit

## Integration Points

### B-Fabric Integration

bfabric-app-runner integrates with B-Fabric through:

- **Workunit definitions** - Load workunit entities (execution and registration)
- **Dataset access** - Download dataset files
- **Resource access** - Download resource files with checksum verification
- **Output registration** - Create resources and datasets
- **Status updates** - Update workunit status (processing → available/failed)

### SLURM Integration

bfabric-app-runner supports SLURM through:

- **Job submission** - Submit workunit as SLURM job
- **Resource allocation** - Request CPUs, memory, walltime
- **Output logging** - Redirect output to SLURM output
- **Job dependencies** - Handle job array dependencies (if applicable)

## Extensibility

bfabric-app-runner is designed for extensibility:

### Custom Input Types

Add new input types by extending Pydantic models in `specs/inputs/`:

```python
# Define new input type
class MyCustomInputSpec(BaseModel):
    type: Literal["my_custom_type"] = "my_custom_type"
    custom_field: str

# Register in InputsSpec
InputSpecType = Annotated[
    ...existing_types...,
    MyCustomInputSpec,
    Field(discriminator="type"),
]
```

### Custom Output Types

Add new output types by extending Pydantic models in `specs/outputs/`:

```python
# Define new output type
class MyCustomOutputSpec(BaseModel):
    type: Literal["my_custom_type"] = "my_custom_type"
    custom_field: str

# Register in OutputsSpec
OutputSpecType = Annotated[
    ...existing_types...,
    MyCustomOutputSpec,
    Field(discriminator="type"),
]
```

### Custom Command Types

Add new command types by extending Pydantic models in `specs/app/commands_spec.py`:

```python
# Define new command type
class MyCustomCommand(BaseModel):
    type: Literal["my_custom"] = "my_custom"
    custom_field: str

# Register in CommandsSpec
CommandSpecType = Annotated[
    ...existing_types...,
    MyCustomCommand,
    Field(discriminator="type"),
]
```

## Security Considerations

### B-Fabric Credentials

bfabric-app-runner uses the same B-Fabric credential configuration as bfabric:

- **Config file:** `~/.bfabricpy.yml`
- **Environment variables:** `BFABRICPY_CONFIG_OVERRIDE`, `BFABRICPY_CONFIG_ENV`
- **Web service passwords:** Required for API access

**Related:** [Configuration Guide](../getting_started/configuration.md)

### SSH Access

Some operations require SSH access for file transfers:

- **Resource copying:** SCP files to B-Fabric storage
- **SSH user:** Configurable via `--ssh-user` flag
- **Key-based auth:** Depends on SSH configuration

### Container Isolation

Docker containers provide isolation but also require consideration:

- **Volume mounting:** Explicit mount points for inputs/outputs
- **B-Fabric config:** `share_bfabric_config` to share credentials with container
- **Network access:** Control with `--network` custom args

## Performance Considerations

### Caching Strategy

bfabric-app-runner implements intelligent caching:

- **Input files:** Download only if missing or checksum mismatched
- **B-Fabric data:** Cache workunit definitions to avoid repeated queries
- **Local files:** Copy only if missing

### Parallel Processing

For large datasets, use chunking to process in parallel:

- **Chunking configuration:** Split data into subsets
- **Parallel execution:** Process chunks simultaneously (with SLURM array jobs)
- **Resource utilization:** Maximize cluster usage

## Related Documentation

- **[App Model UML](./overview.md)** - Visual representation of app structure
- **[App Runner Activity UML](./overview.md)** - Visual representation of workflow
- **[Data Flow](./data_flow.md)** - Detailed data flow explanation
- **[Execution Model](./execution_model.md)** - Detailed execution models
- **[User Guides](../user_guides/index.md)** - Practical usage guides
- **[API Reference](../api_reference/index.md)** - Complete specification documentation

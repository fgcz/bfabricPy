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

## Quick Links

| Section | Description | When to Read |
| ------------------ | ------------------------------------------------ | ---------------------------------------------- |
| **Architecture** | High-level system design and concepts | Understanding system structure |
| **[Overview](./overview.md)** | Comprehensive architecture documentation | Learning all components |
| **[Data Flow](./data_flow.md)** | How data flows through the system | Understanding input→output pipeline |

## Key Concepts

### App Specification (\`app_spec.yml\`)

Defines application structure and execution commands:

- **App metadata** - B-Fabric integration settings
- **Versions** - Multiple app versions with different commands
- **Commands** - Dispatch, process, and collect phases

**Related:** [App Specification Guide](../user_guides/creating_an_app/app_specification.md)

### Input Specification (\`inputs.yml\`)

Defines input data required by the application:

- **Input types** - B-Fabric datasets, resources, local files, static content
- **Integrity checking** - Automatic checksum verification
- **Caching** - Smart download and re-use of files

**Related:** [Input Specification Guide](../user_guides/working_with_inputs/input_specification.md)

### Output Specification (\`outputs.yml\`)

Defines results to register to B-Fabric:

- **Output types** - Resources, datasets, entity links
- **Templating** - Use \`${workunit.id}\` for dynamic filenames
- **Registration** - Automatic association with workunits

**Related:** [Output Specification Guide](../user_guides/working_with_outputs/output_specification.md)

### Workunit Definition

B-Fabric entity representing a work unit to be executed:

- **Execution parameters** - Raw parameters for the app
- **Registration metadata** - Application, container, and storage information
- **Separation of concerns** - Isolate execution logic from registration

**Related:** [Workunit Definition Guide](../../bfabric/docs/advanced_topics/workunit_definitions/index.md)

## Workflow Phases

A complete bfabric-app-runner workflow executes these phases:

\`\`1. Dispatch → 2. Inputs → 3. Process → 4. Outputs → 5. Collect\`\`

| Phase | Purpose | Context |
| ---------- | ---------------------------------------------- | -------------------------------- |
| **Dispatch** | Prepare workflow parameters and context | \`$workunit_ref\`, \`$work_dir\` |
| **Inputs** | Stage input files for processing | \`$work_dir\`, \`inputs.yml\` |
| **Process** | Execute main application logic | \`$chunk_dir\` |
| **Outputs** | Register results to B-Fabric | \`$workunit_ref\`, \`outputs.yml\` |
| **Collect** | Finalize workflow and clean up | \`$workunit_ref\`, \`$chunk_dir\` |

## Execution Models

bfabric-app-runner supports multiple execution models:

| Model | Description | When to Use | Isolation Level |
| ---------- | -------------------------------------------- | ------------------------------------- | --------------- |
| **Direct** | Execute commands on host system | Simple scripts, quick jobs | None |
| **Docker** | Run applications in containers | Isolated, reproducible environments | Full |
| **Python Env**| Run in uv-managed Python environments | Python applications, dependencies | Process-level |

**Details:** See [Execution Model](./execution_model.md) for comprehensive comparison and decision guidance.

## Integration Points

### B-Fabric Integration

bfabric-app-runner integrates with B-Fabric through:

- **Workunit definitions** - Load workunit entities (execution and registration)
- **Dataset access** - Download dataset files for input staging
- **Resource access** - Download resource files with checksum verification
- **Output registration** - Create resources and datasets, create entity links
- **Status updates** - Update workunit status (processing → available/failed)

### SLURM Integration

bfabric-app-runner supports SLURM through:

- **Job submission** - Submit workunits as SLURM jobs
- **Resource allocation** - Request CPUs, memory, walltime
- **Output logging** - Redirect output to SLURM output files
- **Job dependencies** - Handle job array dependencies (if applicable)

## Security Considerations

### B-Fabric Credentials

bfabric-app-runner uses B-Fabric credential configuration:

- **Config file** - \`~/.bfabricpy.yml\` (shared with bfabric)
- **Environment variables** - \`BFABRICPY_CONFIG_OVERRIDE\`, \`BFABRICPY_CONFIG_ENV\`
- **Web service passwords** - Required for API access (not login passwords)

**Related:** [Configuration Guide](../getting_started/configuration.md)

## Performance Considerations

### Caching Strategy

bfabric-app-runner implements intelligent caching:

- **Input files** - Download only if missing or checksum mismatched
- **B-Fabric data** - Cache workunit definitions to avoid repeated queries
- **Local files** - Copy only if missing

### Parallel Processing

For large datasets, use chunking to process in parallel:

- **Chunking configuration** - Split data into subsets
- **Parallel execution** - Process chunks simultaneously (with SLURM array jobs)
- **Resource utilization** - Maximize cluster usage

## Related Documentation

- **[Data Flow](./data_flow.md)** - Detailed data flow through the system
- **[Execution Model](./execution_model.md)** - Execution environments and their trade-offs
- **[Complete Workflow](../user_guides/workflows/complete_workflow.md)** - End-to-end workflow example
- **[User Guides](../user_guides/index.md)** - Practical usage guides
- **[API Reference](../api_reference/index.md)** - Complete specification documentation

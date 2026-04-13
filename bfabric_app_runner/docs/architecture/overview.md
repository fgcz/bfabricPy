## Architecture Overview

### What is bfabric-app-runner?

bfabric-app-runner is a framework for executing computational applications that integrate with B-Fabric,
a laboratory information management system. It manages the full lifecycle of running an application:
fetching input data, executing processing logic, and registering outputs back into B-Fabric.

Applications are defined declaratively through YAML specification files that describe which commands
to run, what inputs to fetch, and how to register outputs. The runner handles orchestration, so
application developers can focus on their processing logic.

### Workflow Phases

An application execution proceeds through four phases:

1. **Dispatch** -- The dispatch command receives a workunit reference and a work directory. It creates
   one or more "chunk" subdirectories, each containing an `inputs.yml` file that declares the inputs
   needed for that chunk. A `chunks.yml` file in the work directory lists all chunk paths. If
   `chunks.yml` is not created by the dispatch command, the runner auto-discovers chunks by scanning
   for subdirectories containing `inputs.yml`.

2. **Inputs** -- For each chunk, the runner reads the chunk's `inputs.yml` and downloads or prepares
   the declared input files into the chunk directory. Inputs can come from B-Fabric (resources,
   datasets, annotations, order FASTAs), from remote files (SSH, local), or be generated from
   static content.

3. **Process** -- The process command is called with the chunk directory as its argument. This is
   where the actual computational work happens. The command can be a direct executable, a Docker
   container, or a managed Python environment.

4. **Outputs / Collect** -- After processing, an optional collect command generates an `outputs.yml`
   file describing results to register. If no collect command is defined, the process command is
   expected to produce `outputs.yml` directly. The runner then registers outputs back into B-Fabric
   (copying resources to storage, saving datasets, creating links).

### Key Components

**Runner** (`bfabric_app_runner.app_runner.runner.Runner`) orchestrates all four phases. It holds
a reference to an `AppVersion` (which defines the commands) and a `Bfabric` client instance.

**AppSpec and AppVersion** define the application configuration. An `AppSpec` contains a
`BfabricAppSpec` (runner version, optional workflow template) and a list of `AppVersion` entries.
Each `AppVersion` specifies a version string and a `CommandsSpec` with dispatch, process, and
optional collect commands. App specs support Mako templating with variables like `${app.id}`,
`${app.name}`, and `${app.version}`.

**Command executors** run the actual commands. Four command types are available:

- `CommandShell` -- runs a command string split by spaces (deprecated in favor of `exec`)
- `CommandExec` -- runs a command split by `shlex.split`, with optional environment variables and
  PATH prepending
- `CommandDocker` -- runs a command inside a Docker or Podman container, with configurable mounts,
  environment, networking, and custom arguments
- `CommandPythonEnv` -- provisions a Python virtual environment from a pylock file and runs a
  command inside it, with optional extra local dependencies and caching

**Resolver** resolves input specifications into concrete file references. Each input type has a
dedicated resolver. The result is a `ResolvedInputs` object containing `ResolvedFile`,
`ResolvedStaticFile`, and `ResolvedDirectory` entries that can be prepared (downloaded/written) or
cleaned.

**Output registration** reads `outputs.yml` and registers results into B-Fabric. Three output types
are supported: `CopyResourceSpec` (SCP a file to storage), `SaveDatasetSpec` (register a CSV/TSV
as a dataset), and `SaveLinkSpec` (attach a URL link to an entity).

### How Chunks Work

The chunking mechanism allows applications to split work into independent units. During dispatch,
the application creates subdirectories under the work directory -- one per chunk. Each chunk
directory contains its own `inputs.yml` (and after processing, `outputs.yml`).

The `ChunksFile` model tracks which chunks exist. It can be written explicitly by the dispatch
command as `chunks.yml`, or the runner auto-discovers chunks by scanning for subdirectories
that contain an `inputs.yml` file.

The runner processes chunks sequentially: for each chunk, it prepares inputs, runs the process
command, runs the optional collect command, and registers outputs.

### Action Types

The CLI exposes the workflow phases as individual actions:

- `ActionDispatch` -- runs only the dispatch phase
- `ActionInputs` -- prepares inputs for all chunks
- `ActionProcess` -- runs the process command for all chunks
- `ActionOutputs` -- runs collect and registers outputs for all chunks
- `ActionRun` -- runs all phases end-to-end

These actions allow developers to test individual phases during development.

### Dispatch Strategies

The `dispatch` module provides reusable dispatch strategies for common patterns:

- **DispatchIndividualResources** -- creates one chunk per input resource, useful when each
  resource should be processed independently
- **DispatchSingleResourceFlow** -- creates a single chunk for all resources, useful when
  resources are processed together
- **DispatchSingleDatasetFlow** -- creates a single chunk driven by a dataset, useful when
  a dataset defines the processing parameters

These strategies handle the creation of chunk directories, writing `inputs.yml` files, and
producing the `chunks.yml` manifest.

### App model

```{eval-rst}
.. uml:: uml/app_model.plantuml
```

### App runner activity diagram

```{eval-rst}
.. uml:: uml/app_runner_activity.plantuml
```

# bfabric-app-runner Documentation

bfabric-app-runner provides a declarative, YAML-based workflow system for executing bioinformatics applications on B-Fabric workunits.

## Key Features

### Declarative App Specifications

Define your applications using YAML configuration files with:

- **Multi-version support**: Define multiple app versions in a single specification
- **Version management**: Easy versioning and rollback capabilities
- **Mako templating**: Dynamic configuration with `${app.id}`, `${app.name}`, `${app.version}`
- **Separate concerns**: Clear separation of dispatch, process, and collect phases

### Automated Input Staging

Automatically prepare and stage input data from various sources:

- **B-Fabric datasets**: Direct dataset access from B-Fabric
- **B-Fabric resources**: Resource files with integrity checking
- **Static files**: Embedded file content directly in YAML
- **Smart caching**: Only download missing or outdated files
- **Flexible specifications**: Define inputs declaratively with validation

### Multiple Execution Environments

Execute your applications in the environment that suits you:

| Environment | Description |
| ---------------- | ---------------------------------------------------- |
| **Docker** | Containerized execution with isolated dependencies |
| **Shell** | Direct shell command execution |
| **Python venv** | Python virtual environments for Python apps |

### Output Registration

Automatically register your outputs back to B-Fabric:

- **Resource copies**: Copy files to B-Fabric storage
- **Dataset creation**: Create datasets from CSV/tabular data
- **Flexible registration**: Declarative output specifications
- **Workunit integration**: Automatic association with workunits

### Workunit Workflow Management

End-to-end workunit execution with:

- **Workunit definitions**: YAML-based workunit configuration
- **SLURM integration**: Submit jobs to SLURM schedulers
- **Status tracking**: Automatic status updates (processing → available/failed)
- **Chunking support**: Parallel processing of work units
- **Dispatch/Process/Collect**: Standardized workflow phases

### Developer Tools

Rich CLI for development and testing:

```bash
# Validate specifications
bfabric-app-runner validate app-spec
bfabric-app-runner validate inputs-spec
bfabric-app-runner validate outputs-spec

# Prepare and test locally
bfabric-app-runner prepare workunit <workunit_ref>
bfabric-app-runner inputs prepare inputs.yml .
make help  # Shows available commands in workunit folder

# Run end-to-end
bfabric-app-runner run workunit <app_spec.yml> <workunit_ref>
```

## Installation

```bash
# Install the latest release
uv tool install bfabric_app_runner

# Or install a development version
uv tool install bfabric_app_runner@git+https://github.com/fgcz/bfabricPy.git@main#egg=bfabric_app_runner&subdirectory=bfabric_app_runner
```

See [Installation Guide](getting_started/installation.md) for more options.

## Documentation Structure

````{note}
**Legacy Architecture Documentation**

The following sections contain archived/legacy architecture documentation that has been superseded by user guides and API reference. This information is preserved for historical reference but may not reflect current best practices.

```{toctree}
:maxdepth: 1
:caption: Archived Architecture Documentation
architecture/index
architecture/data_flow
architecture/execution_model
````

## Installation

This documentation is organized by **what you want to do** rather than API structure:

| Section | Description |
| ------------------- | ------------------------------------------------------- |
| **Getting Started** | Installation, quick start, configuration |
| **User Guides** | Task-based tutorials and practical examples |
| **API Reference** | Complete, auto-generated specification documentation |
| **Resources** | Troubleshooting, best practices, examples, changelog |

````{note}
**Legacy Architecture Documentation**

The following sections contain archived/legacy architecture documentation that has been superseded by user guides and API reference. This information is preserved for historical reference but may not reflect current best practices.

```{toctree}
:maxdepth: 1
:caption: Archived Architecture Documentation
architecture/index
architecture/data_flow
architecture/execution_model
````

## Installation

```bash
# Install library
pip install bfabric

# Install command-line tools
uv tool install bfabric-scripts
```

See [Installation Guide](../../bfabric/docs/getting_started/installation.md) for more options.

## Version

Current version and history: [Changelog](resources/changelog.md)

## Documentation Structure

This documentation is organized by **what you want to do** rather than API structure:

| Section | Description |
| ------------------- | ------------------------------------------------------- |
| **Getting Started** | Installation, quick start, configuration |
| **User Guides** | Task-based tutorials and practical examples |
| **API Reference** | Complete, auto-generated specification documentation |
| **Resources** | Troubleshooting, best practices, examples, changelog |

## Support

- **Issues**: https://github.com/fgcz/bfabricPy/issues
- **Documentation**: https://github.com/fgcz/bfabricPy

## Related Documentation

- **[bfabric Documentation](../../bfabric/index.md)** - Core bfabricPy library for interacting with B-Fabric
- **[B-Fabric](https://fgcz-bfabric.uzh.ch/bfabric/)** - The B-Fabric laboratory information management system

See [Installation Guide](../../bfabric/docs/getting_started/installation.md) for more options.

## Version

Current version and history: [Changelog](resources/changelog.md)

````{note}
**Legacy Architecture Documentation**

The following sections contain archived/legacy architecture documentation that has been superseded by user guides and API reference. This information is preserved for historical reference but may not reflect current best practices.

```{toctree}
:maxdepth: 1
:caption: Archived Architecture Documentation
architecture/index
architecture/data_flow
architecture/execution_model
````

## Support

- **Issues**: https://github.com/fgcz/bfabricPy/issues
- **Documentation**: https://github.com/fgcz/bfabricPy

## Related Documentation

- **[bfabric Documentation](../bfabric/index.md)** - Core bfabricPy library for interacting with B-Fabric
- **[B-Fabric](https://fgcz-bfabric.uzh.ch/bfabric/)** - The B-Fabric laboratory information management system

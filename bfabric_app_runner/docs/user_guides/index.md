# User Guides

Practical guides for common tasks and workflows with bfabric-app-runner.

```{toctree}
:maxdepth: 1
:caption: Creating an App
creating_an_app/app_specification
creating_an_app/defining_commands
creating_an_app/versioning
```

```{toctree}
:maxdepth: 1
:caption: Working with Inputs
working_with_inputs/input_specification
working_with_inputs/staging_files
working_with_inputs/bfabric_datasets
working_with_inputs/bfabric_resources
working_with_inputs/static_files
```

```{toctree}
:maxdepth: 1
:caption: Working with Outputs
working_with_outputs/output_specification
working_with_outputs/registering_outputs
working_with_outputs/common_patterns
```

```{toctree}
:maxdepth: 1
:caption: Execution Environments
execution/docker_environment
execution/shell_environment
execution/python_environment
execution/slurm_integration
```

```{toctree}
:maxdepth: 1
:caption: Workflows
workflows/complete_workflow
workflows/testing_locally
workflows/production_deployment
workflows/chunking_parallelization
```

```{toctree}
:maxdepth: 2
:caption: CLI Reference
cli_reference/running_apps
cli_reference/developer_tools
cli_reference/common_scenarios
```

## Guides Overview

| Guide | Description | Skill Level |
| -------------------------------------------------------- | -------------------------------------------------------- | ------------ |
| **Creating an App** | Define and version bioinformatics applications | Intermediate |
| [App Specification](creating_an_app/app_specification.md) | Create app_spec.yml with versions and commands | Beginner |
| [Defining Commands](creating_an_app/defining_commands.md) | Configure dispatch/process/collect commands | Intermediate |
| [Versioning](creating_an_app/versioning.md) | Manage multiple app versions | Intermediate |
| **Working with Inputs** | Prepare and stage input data | Beginner |
| [Input Specification](working_with_inputs/input_specification.md) | Define inputs in inputs.yml | Beginner |
| [Staging Files](working_with_inputs/staging_files.md) | Download and prepare input files | Beginner |
| [B-Fabric Datasets](working_with_inputs/bfabric_datasets.md) | Use datasets from B-Fabric | Beginner |
| [B-Fabric Resources](working_with_inputs/bfabric_resources.md) | Use resources from B-Fabric | Beginner |
| [Static Files](working_with_inputs/static_files.md) | Embed files directly in YAML | Intermediate |
| **Working with Outputs** | Register results to B-Fabric | Intermediate |
| [Output Specification](working_with_outputs/output_specification.md) | Define outputs in outputs.yml | Intermediate |
| [Registering Outputs](working_with_outputs/registering_outputs.md) | Register files to B-Fabric | Intermediate |
| [Common Patterns](working_with_outputs/common_patterns.md) | Typical output scenarios | Intermediate |
| **Execution Environments** | Configure app execution | Intermediate |
| [Docker Environment](execution/docker_environment.md) | Run apps in Docker containers | Intermediate |
| [Shell Environment](execution/shell_environment.md) | Execute shell commands | Beginner |
| [Python Environment](execution/python_environment.md) | Run Python apps in virtual environments | Advanced |
| [SLURM Integration](execution/slurm_integration.md) | Submit jobs to SLURM scheduler | Advanced |
| **Workflows** | End-to-end workflows | Intermediate |
| [Complete Workflow](workflows/complete_workflow.md) | Full app execution from start to finish | Intermediate |
| [Testing Locally](workflows/testing_locally.md) | Develop and test apps locally | Intermediate |
| [Production Deployment](workflows/production_deployment.md) | Deploy to production environment | Advanced |
| [Chunking & Parallelization](workflows/chunking_parallelization.md) | Process work in parallel chunks | Advanced |
| **CLI Reference** | Command-line interface documentation | All Levels |
| [Running Apps](cli_reference/running_apps.md) | Production CLI commands | All Levels |
| [Developer Tools](cli_reference/developer_tools.md) | Testing and validation commands | All Levels |
| [Common Scenarios](cli_reference/common_scenarios.md) | CLI usage patterns and examples | All Levels |

## Common Workflows

- **[Complete App Development](workflows/complete_workflow.md)** - From app spec to production deployment
- **[Local Testing](workflows/testing_locally.md)** - Test your app before deployment
- **[Input Management](working_with_inputs/staging_files.md)** - Prepare and stage input files
- **[Docker Deployment](execution/docker_environment.md)** - Containerize and deploy apps
- **[Output Registration](working_with_outputs/registering_outputs.md)** - Register results to B-Fabric
- **[Production Workflows](workflows/production_deployment.md)** - Deploy to production SLURM

## Quick Links

### I'm Getting Started

- [Quick Start Tutorial](../getting_started/quick_start.md) - 10-minute hands-on tutorial
- [Installation Guide](../getting_started/installation.md) - Installation options and troubleshooting
- [Configuration Guide](../getting_started/configuration.md) - B-Fabric credentials setup

### I Want to Create an App

- [App Specification](creating_an_app/app_specification.md) - Create your first app_spec.yml
- [Defining Commands](creating_an_app/defining_commands.md) - Configure app commands
- [Versioning Guide](creating_an_app/versioning.md) - Manage multiple versions

### I Need to Work with Data

- [Input Specification](working_with_inputs/input_specification.md) - Define your inputs
- [B-Fabric Datasets](working_with_inputs/bfabric_datasets.md) - Use B-Fabric datasets
- [B-Fabric Resources](working_with_inputs/bfabric_resources.md) - Use B-Fabric resources
- [Output Specification](working_with_outputs/output_specification.md) - Define your outputs

### I Want to Deploy to Production

- [Complete Workflow](workflows/complete_workflow.md) - End-to-end execution
- [SLURM Integration](execution/slurm_integration.md) - Job scheduling
- [Production Deployment](workflows/production_deployment.md) - Production best practices

### I Need CLI Reference

- [Running Apps](cli_reference/running_apps.md) - Production commands
- [Developer Tools](cli_reference/developer_tools.md) - Testing and validation
- [Common Scenarios](cli_reference/common_scenarios.md) - Usage patterns

## Next Steps

After completing the getting started guides, explore user guides based on your needs:

| Your Goal | Start Here |
| --------------------------------------------- | ----------------------------------------- |
| Create a new bioinformatics app | [App Specification](creating_an_app/app_specification.md) |
| Prepare input data from B-Fabric | [Input Specification](working_with_inputs/input_specification.md) |
| Deploy with Docker | [Docker Environment](execution/docker_environment.md) |
| Run on SLURM scheduler | [SLURM Integration](execution/slurm_integration.md) |
| Register outputs to B-Fabric | [Output Registration](working_with_outputs/registering_outputs.md) |
| Test locally before production | [Testing Locally](workflows/testing_locally.md) |

## Need Help?

- See [Troubleshooting](../resources/troubleshooting.md) for common issues
- Check [Best Practices](../resources/best_practices.md) for guidelines
- Review [Examples](../resources/examples/) for working code
- Report issues on [GitHub](https://github.com/fgcz/bfabricPy/issues)

## Related Documentation

- [Quick Start Tutorial](../getting_started/quick_start.md) - Your first bfabric-app-runner workflow
- [API Reference](../api_reference/index.md) - Complete specification documentation
- [Architecture](../architecture/index.md) - System design and data flow

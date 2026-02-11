# Getting Started

Welcome to bfabric-app-runner! This section will help you get up and running quickly.

```{toctree}
:maxdepth: 1
installation
quick_start
configuration
```

## What is bfabric-app-runner?

bfabric-app-runner is a declarative, YAML-based workflow system for executing bioinformatics applications on B-Fabric workunits. It provides:

- **Declarative app specifications** - Define apps in YAML with multi-version support
- **Automated input staging** - Fetch and prepare inputs from B-Fabric datasets/resources
- **Multiple execution environments** - Run apps in Docker, shell, or Python virtual environments
- **Output registration** - Automatically register results back to B-Fabric
- **Workunit management** - End-to-end workflow execution with status tracking
- **SLURM integration** - Submit jobs to SLURM schedulers

## Who Should Use This?

| User Type | What You'll Do |
| ---------------------- | --------------------------------------------------------- |
| **Application Developers** | Define and version bioinformatics applications |
| **Workflow Engineers** | Orchestrate multi-step processing pipelines |
| **Researchers** | Run bioinformatics tools on B-Fabric workunits |
| **System Administrators** | Integrate apps with SLURM and production schedulers |

## Installation Requirements

Before installing bfabric-app-runner, ensure you have:

- **Python**: 3.11 or higher (for uv tool installation)
- **uv**: Recommended package manager for installing CLI tools
- **B-Fabric access**: Account with appropriate permissions
- **bfabric** installed: Core bfabricPy library (for workunit integration)

See [Installation Guide](installation.md) for detailed installation instructions.

## Quick Start Path

Follow these steps to get started:

1. **[Install bfabric-app-runner](installation.md)** - Install the CLI tool
2. **[Quick Start Tutorial](quick_start.md)** - 10-minute hands-on tutorial
3. **[Configuration Guide](configuration.md)** - Set up your B-Fabric credentials

## What You'll Learn

After completing the getting started guides, you'll know how to:

- ✅ Install and verify bfabric-app-runner
- ✅ Create a basic app specification
- ✅ Define input and output specifications
- ✅ Prepare and execute a workunit
- ✅ Register outputs back to B-Fabric

## Next Steps

After getting started, explore our **[User Guides](../user_guides)** for practical examples and workflows:

- **[Creating an App](../user_guides/creating_an_app/)** - Define and version your applications
- **[Working with Inputs](../user_guides/working_with_inputs/)** - Stage inputs from various sources
- **[Working with Outputs](../user_guides/working_with_outputs/)** - Register results to B-Fabric
- **[Execution Environments](../user_guides/execution/)** - Configure Docker, shell, or Python execution
- **[Complete Workflows](../user_guides/workflows/)** - End-to-end workflow examples
- **[CLI Reference](../user_guides/cli_reference/)** - Command-line interface documentation

## Quick Links

- [Installation Guide](installation.md) - Installation options and verification
- [Quick Start Tutorial](quick_start.md) - Your first bfabric-app-runner workflow
- [Configuration Guide](configuration.md) - B-Fabric credentials and settings
- [User Guides](../user_guides/index.md) - Practical tutorials and examples

## Need Help?

- See [Troubleshooting](../resources/troubleshooting.md) for common issues
- Check [Best Practices](../resources/best_practices.md) for guidelines
- Review [Examples](../resources/examples/) for working code
- Report issues on [GitHub](https://github.com/fgcz/bfabricPy/issues)

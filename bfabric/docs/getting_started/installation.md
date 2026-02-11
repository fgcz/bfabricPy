# Installation

bfabricPy consists of two main packages:

- **`bfabric`** - The core Python library for programmatic access to the bfabric system
- **`bfabric-scripts`** - Optional command-line tools, primarily the useful `bfabric-cli` utility

Choose your installation method based on how you plan to use bfabricPy.

______________________________________________________________________

## Installing the Core Library (`bfabric`)

Use this if you want to write Python scripts or integrate bfabric functionality into your applications.

### For Python Projects (Recommended)

Add `bfabric` to your project's dependencies in `pyproject.toml`:

```toml
[project]
dependencies = [
    "bfabric>=1.16.0,<2.0.0"
]
```

For production use, consider locking to a specific version to avoid unexpected changes.

### Installing from Git

For development versions or specific commits:

```toml
[project]
dependencies = [
    "bfabric @ git+https://github.com/fgcz/bfabricPy.git@main&subdirectory=bfabric#egg=bfabric",
]
```

### With pip

```bash
pip install bfabric
```

### With uv

```bash
uv pip install bfabric
```

______________________________________________________________________

## Installing Command-Line Tools (`bfabric-scripts`)

The `bfabric-scripts` package provides the **`bfabric-cli`** command-line tool, which is useful for:

- Quick one-off queries and operations
- Batch processing in shell scripts
- Interactive data exploration
- Testing API calls without writing Python code

**Note:** `bfabric-scripts` also contains legacy scripts that are maintained for compatibility but are not actively developed. The modern and recommended tool is `bfabric-cli`.

### Using uv tool (Recommended for CLI)

The best way to install command-line tools is using `uv tool`, which creates an isolated virtual environment:

```bash
# Install bfabric-scripts
uv tool install bfabric-scripts

# Upgrade to latest version
uv tool upgrade bfabric-scripts
```

This makes `bfabric-cli` available system-wide and simplifies upgrades.

______________________________________________________________________

## Which Should You Install?

bfabricPy provides two components that are installed separately:

| Component | Type | Install Method | Best For |
|-----------|------|----------------|-----------|
| **bfabric** | Python package | `pip install bfabric` or `uv pip install bfabric` | Python projects, scripts, applications |
| **bfabric-scripts** | CLI tool | `uv tool install bfabric-scripts` | Command-line usage, quick tasks, shell scripts |

**Install both if:** You plan to use both Python programming and command-line tools.

**Note:** `bfabric` is a Python package dependency. `bfabric-scripts` is a CLI tool installed separately using `uv tool`.

______________________________________________________________________

## Development Installation

For contributing to bfabricPy, see the [Contributing Guide](https://github.com/fgcz/bfabricPy/blob/main/CONTRIBUTING.md).

______________________________________________________________________

## Verifying Installation

### Check the Core Library

```bash
python -c "import bfabric; print(bfabric.__version__)"
```

### Check Command-Line Tools

If you installed `bfabric-scripts`:

```bash
bfabric-cli --version
bfabric-cli --help
```

This should display the CLI version and available commands.

______________________________________________________________________

## About bfabric-cli

`bfabric-cli` is the modern command-line interface provided by `bfabric-scripts`. It offers:

- **Entity queries** - Find and display datasets, samples, workunits, etc.
- **Data retrieval** - Download files and metadata
- **Bulk operations** - Process multiple entities efficiently
- **Convenient output formats** - JSON, tables, CSV
- **Shell-friendly** - Easy to use in scripts and pipelines

### Example bfabric-cli Usage

```bash
# Find recent datasets
bfabric-cli entity list --type dataset --limit 10

# Get detailed information about a specific entity
bfabric-cli entity show --id 12345

# Search for samples by name
bfabric-cli entity search --type sample --query "my_sample"
```

For comprehensive `bfabric-cli` documentation, see the [bfabric-cli User Guide](../user_guides/bfabric-cli/index).

______________________________________________________________________

## System Requirements

- **Python**: 3.11 or higher
- **Dependencies**: Installed automatically via pip/uv

The `bfabric` package and `bfabric-scripts` share the same Python version requirements.

______________________________________________________________________

## Next Steps

After installing the packages:

1. **Configure your credentials**: [Configuration Guide](configuration.md)
2. **Try it out**:
   - For Python usage: [Quick Start Tutorial](quick_start)
   - For CLI usage: [bfabric-cli User Guide](../user_guides/bfabric-cli/index)

______________________________________________________________________

## Related Documentation

- [Configuration Guide](configuration) - Setting up config files and environment variables
- [Quick Start Tutorial](quick_start) - Your first bfabricPy script
- [bfabric-cli User Guide](../user_guides/bfabric-cli/index) - Command-line interface documentation
- [Creating a Client](../user_guides/creating_a_client/index) - Using bfabric in Python code

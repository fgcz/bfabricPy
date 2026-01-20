# Installation

bfabricPy is available on PyPI and can be installed in several ways.

## Using uv tool (Recommended for Scripts)

The recommended way to install the command-line scripts is using `uv tool`:

```bash
# Install bfabric-scripts
uv tool install bfabric-scripts

# Upgrade to latest version
uv tool upgrade bfabric-scripts
```

This creates a separate virtual environment for bfabric-scripts and makes upgrades easy.

## Adding as a Package Dependency

For Python projects, add `bfabric` to your dependencies in `pyproject.toml`:

```toml
[project]
dependencies = [
    "bfabric==1.16.1"  # Specify the version you need
]
```

### Installing from Git

For development versions, install directly from the repository:

```toml
[project]
dependencies = [
    "bfabric @ git+https://github.com/fgcz/bfabricPy.git@stable&subdirectory=bfabric#egg=bfabric",
]
```

## Installing with pip

```bash
# Install bfabric library
pip install bfabric

# Install bfabric-scripts
pip install bfabric-scripts
```

## Development Installation

For contributing to bfabricPy, see the [Contributing Guide](../../resources/contributing.md).

## Verifying Installation

```bash
# Check bfabric installation
python -c "import bfabric; print(bfabric.__version__)"

# Check bfabric-scripts
bfabric-cli --help
```

## Next Steps

After installation, proceed to:

- [Quick Start Tutorial](quick_start.md) - Your first bfabricPy script
- [Configuration Guide](configuration.md) - Setting up your credentials

## System Requirements

- **Python**: 3.11 or higher
- **Dependencies**: Installed automatically via pip/uv

## Related Documentation

- [Configuration Guide](configuration.md) - Setting up config files and environment variables
- [Creating a Client](../user_guides/creating_a_client/index.md) - Using your installation

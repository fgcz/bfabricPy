# Installation

bfabric-app-runner is a command-line tool for executing bioinformatics applications on B-Fabric workunits using declarative YAML specifications.

## Prerequisites

Before installing bfabric-app-runner, ensure you have:

- **Python**: 3.11 or higher
- **uv**: Fast Python package manager (recommended for CLI tool installation)
  ```bash
  # Install uv (if not already installed)
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **bfabric**: Core bfabricPy library (for B-Fabric integration)
  ```bash
  uv tool install bfabric
  ```
- **B-Fabric account**: With appropriate permissions for your use case
- **Docker** (optional): Required for Docker-based execution environments
- **SLURM** (optional): Required for SLURM scheduler integration

## Installing bfabric-app-runner

### Recommended: Using uv tool

The best way to install bfabric-app-runner is using `uv tool`, which creates an isolated virtual environment and makes the CLI available system-wide:

```bash
# Install the latest released version
uv tool install bfabric_app_runner

# Upgrade to the latest version
uv tool upgrade bfabric_app_runner
```

This makes `bfabric-app-runner` available system-wide and simplifies upgrades.

### Installing from Git

For development versions or specific commits:

```bash
# Install from main branch
uv tool install bfabric_app_runner@git+https://github.com/fgcz/bfabricPy.git@main#egg=bfabric_app_runner&subdirectory=bfabric_app_runner

# Install from a specific branch or tag
uv tool install bfabric_app_runner@git+https://github.com/fgcz/bfabricPy.git@v1.2.3#egg=bfabric_app_runner&subdirectory=bfabric_app_runner
```

### Using pip

If you prefer pip over uv:

```bash
# Install the latest released version
pip install bfabric_app_runner

# Install from git
pip install git+https://github.com/fgcz/bfabricPy.git@main#subdirectory=bfabric_app_runner
```

```{note}
When using pip, the `bfabric-app-runner` command will be installed in your Python environment's `bin` directory. Ensure this directory is in your PATH.
```

## Verifying Installation

After installation, verify that bfabric-app-runner is working correctly:

```bash
# Check the version
bfabric-app-runner --version

# Show available commands
bfabric-app-runner --help
```

You should see output showing the version number and available command groups:

```
B-Fabric App Runner - Execute bioinformatics applications on your B-Fabric workunits.

Commands:
  inputs      Prepare input files for an app.
  outputs     Register output files of an app.
  validate    Validate yaml files.
  action      Executes an action of a prepared workunit
  prepare     Prepare a workunit for execution.
  run         Run an app end-to-end.
```

## Installing bfabric (Core Library)

bfabric-app-runner depends on the bfabric core library for B-Fabric integration. If you don't have it installed:

```bash
# Using uv tool (recommended)
uv tool install bfabric

# Or using pip
pip install bfabric
```

See the [bfabric Installation Guide](../../bfabric/docs/getting_started/installation.md) for more options.

## Configuring B-Fabric Credentials

bfabric-app-runner uses the same B-Fabric credentials configuration as the bfabric core library. Configure your credentials in `~/.bfabricpy.yml`:

```yaml
# ~/.bfabricpy.yml

GENERAL:
  default_config: PRODUCTION

PRODUCTION:
  login: yourBfabricLogin
  password: yourBfabricWebPassword
  base_url: https://fgcz-bfabric.uzh.ch/bfabric/

TEST:
  login: yourBfabricLogin
  password: yourBfabricWebPassword
  base_url: https://fgcz-bfabric-test.uzh.ch/bfabric/
```

```{important}
The password in your config file is not your login password. You can find your web service password on your B-Fabric profile page.
```

See [Configuration Guide](configuration.md) for more details on B-Fabric configuration.

## System Requirements

| Component | Requirement |
| ----------- | ------------------------------------------------------ |
| **Python** | 3.11 or higher |
| **uv** | Optional but recommended for CLI tool installation |
| **bfabric** | Required for B-Fabric integration |
| **Docker** | Required for Docker-based execution environments |
| **SLURM** | Required for SLURM scheduler integration (optional) |

## Development Installation

For contributing to bfabric-app-runner, see the [Contributing Guide](https://github.com/fgcz/bfabricPy/blob/main/CONTRIBUTING.md).

## Upgrading bfabric-app-runner

### Using uv tool

```bash
# Upgrade to the latest version
uv tool upgrade bfabric_app_runner
```

### Using pip

```bash
# Upgrade to the latest version
pip install --upgrade bfabric_app_runner
```

## Uninstalling

### Using uv tool

```bash
uv tool uninstall bfabric_app_runner
```

### Using pip

```bash
pip uninstall bfabric_app_runner
```

## Next Steps

After installing bfabric-app-runner:

1. **Configure B-Fabric credentials**: [Configuration Guide](configuration.md)
2. **Try it out**: [Quick Start Tutorial](quick_start.md)
3. **Learn more**: [User Guides](../user_guides/index.md)

## Troubleshooting

### Command not found

If you see `command not found: bfabric-app-runner`:

```bash
# Check if uv tool installed it
uv tool list | grep bfabric_app_runner

# Add uv tools to your PATH (if using bash/zsh)
export PATH="$HOME/.local/bin:$PATH"
# Add this to your ~/.bashrc or ~/.zshrc
```

### Python version too old

If you get an error about Python version:

```bash
# Check your Python version
python --version

# You need Python 3.11 or higher
# Install a newer Python or use pyenv
```

### B-Fabric connection errors

If you see authentication or connection errors:

```bash
# Verify bfabric is configured
bfabric-cli --version

# Test B-Fabric connection
bfabric-cli api read workunit --limit 1
```

See [Configuration Guide](configuration.md) for help setting up B-Fabric credentials.

### Docker not found

If you're using Docker commands and get "docker not found":

```bash
# Install Docker
# macOS: https://docs.docker.com/desktop/install/mac-install/
# Linux: https://docs.docker.com/engine/install/

# Verify installation
docker --version
```

## Related Documentation

- [Configuration Guide](configuration.md) - B-Fabric credentials and settings
- [Quick Start Tutorial](quick_start.md) - Your first bfabric-app-runner workflow
- [User Guides](../user_guides/index.md) - Practical tutorials and examples
- [Troubleshooting](../resources/troubleshooting.md) - Common issues and solutions

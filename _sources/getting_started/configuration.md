# Configuration

bfabricPy can be configured through config files, environment variables, or code.

## Configuration File (Recommended)

Create a YAML file at `~/.bfabricpy.yml`:

```yaml
# ~/.bfabricpy.yml

GENERAL:
  default_config: PRODUCTION  # Default environment to use

PRODUCTION:
  login: yourBfabricLogin
  password: yourBfabricWebServicePassword  # Get from B-Fabric profile
  base_url: https://fgcz-bfabric.uzh.ch/bfabric/

TEST:
  login: yourBfabricLogin
  password: yourBfabricWebServicePassword
  base_url: https://fgcz-bfabric-test.uzh.ch/bfabric/
```

### Web Service Password

The password in your config file is **NOT** your login password. Find your web service password:

1. Log into B-Fabric web interface
2. Go to your profile page
3. Find the "Web Service Password" section

```{warning}
This password authenticates you to the B-Fabric webservices.
Make sure not to share it with others and ensure proper permissions for the configuration file.
```

### Multiple Environments

You can define multiple environments (e.g., PRODUCTION, TEST) and switch between them:

```bash
# Use default environment
python script.py

# Use TEST environment
BFABRICPY_CONFIG_ENV=TEST python script.py
```

### Using Multiple Config Files

Use a custom config file location:

```python
from bfabric import Bfabric
from pathlib import Path

client = Bfabric.connect(
    config_file_path=Path("/custom/path/config.yml"),
    config_file_env="PRODUCTION",
)
```

## Environment Variables

bfabricPy supports several environment variables for configuration.

### BFABRICPY_CONFIG_ENV

Sets the default environment to use:

```bash
export BFABRICPY_CONFIG_ENV=TEST
python script.py  # Will use TEST environment
```

### BFABRICPY_CONFIG_OVERRIDE

Complete configuration override (highest priority). Used primarily for integration tests, where it needs to be prevented that the regular config file leads to the wrong B-Fabric instance being modified.

```bash
export BFABRICPY_CONFIG_OVERRIDE='{"client": {"base_url": "https://fgcz-bfabric.uzh.ch/bfabric/"}, "auth": {"login": "myuser", "password": "mypass"}}'
python script.py  # Uses this config, ignoring ~/.bfabricpy.yml
```

### Priority Order {#priority-order}

Configuration is loaded in this order (highest to lowest):

1. **BFABRICPY_CONFIG_OVERRIDE** - Complete config override
2. **config_file_env parameter** in code
3. **BFABRICPY_CONFIG_ENV** environment variable
4. **default_config** in config file

## Code-Based Configuration

For maximum flexibility, you can provide configuration in code:

```python
from bfabric import Bfabric
from bfabric.config import BfabricAuth, BfabricClientConfig

# Create config programmatically
client_config = BfabricClientConfig(
    base_url="https://fgcz-bfabric.uzh.ch/bfabric/",
    engine="zeep",  # or "suds"
)

auth = BfabricAuth(
    login="your_login",
    password="your_password",
)

# Note: This is for advanced use cases. See API Reference for details.
```

## Token-Based Configuration (Web Apps)

For web applications that receive B-Fabric tokens, see:

- [Server/Webapp Usage](../user_guides/creating_a_client/server_webapp_usage.md)

## Best Practices

1. **Never commit config files to git** - Use environment variables for CI/CD
2. **Use TEST environment** for development and testing
3. **Separate credentials** - Different users for different projects/environments
4. **Document your environments** - Comment in config files to explain each environment's purpose
5. **Use environment variables** for secrets in containerized deployments

## See Also

- [Installation Guide](installation.md) - Installation options
- [Creating a Client Guide](../user_guides/creating_a_client/index.md) - How to use configuration
- [Server/Webapp Configuration](../user_guides/creating_a_client/server_webapp_usage.md) - Token-based auth
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

# Creating a Client for Interactive and Scripted Usage

This guide covers how to create a `Bfabric` client for interactive sessions and scripts, where you control the
configuration directly through config files or environment variables.

## Overview

For interactive and scripted usage, use `Bfabric.connect()` to create a client instance. This method is designed for
situations where:

- You're running scripts locally or in controlled environments
- You have access to a configuration file with credentials
- You need simple, synchronous API access
- You want to quickly switch between environments (e.g., PRODUCTION vs TEST)

## Prerequisites

Before creating a client, set up your configuration file. See the [Configuration Guide](../../getting_started/configuration.md) for detailed instructions on:

- Creating `~/.bfabricpy.yml` with your credentials
- Setting up multiple environments (PRODUCTION, TEST)
- Using environment variables
- Configuration priority and overrides

## Creating a Client

### Basic Usage

```python
from bfabric import Bfabric

client = Bfabric.connect()
```

This uses your `~/.bfabricpy.yml` config file with the default environment. See [Configuration Guide](../../getting_started/configuration.md#priority-order) for how the environment is selected.

### Specifying an Environment

You can explicitly specify which environment to use:

```python
# Use the PRODUCTION environment
client = Bfabric.connect(config_file_env="PRODUCTION")

# Use the TEST environment
client = Bfabric.connect(config_file_env="TEST")
```

The `config_file_env` parameter takes precedence over the `BFABRICPY_CONFIG_ENV` environment variable.

### Using a Custom Config File

If your config file is in a non-standard location:

```python
from pathlib import Path

custom_config_path = Path("/path/to/custom/config.yml")
client = Bfabric.connect(
    config_file_path=custom_config_path, config_file_env="PRODUCTION"
)
```

### Temporarily Changing Authentication

The `with_auth()` context manager allows you to temporarily set authentication for a `Bfabric` client. This is useful when
authenticating multiple users to avoid accidental use of the wrong credentials:

```python
from bfabric import Bfabric
from bfabric.config import BfabricAuth

client = Bfabric.connect()

# Temporarily use different credentials
with client.with_auth(BfabricAuth(login="other_user", password="other_pass")):
    # All operations in this block use different authentication
    samples = client.read(endpoint="sample", obj={"name": "Test"})

# Authentication is restored after the block
samples = client.read(endpoint="sample", obj={"name": "Test"})

print(f"Current user: {client.auth.login}")  # Shows original user
```

### Without Authentication

For certain use cases (e.g., tests, read-only operations on public endpoints), you may want to create a client without
authentication:

```python
# Disable authentication - useful for tests
client = Bfabric.connect(config_file_env=None, include_auth=False)
```

```{warning}
Without authentication, you won't be able to perform operations that require credentials, such as creating or updating
entities.
```

## Verification

Always verify you're using the correct environment:

```python
from bfabric import Bfabric

client = Bfabric.connect()
print(f"Connected to: {client.config.base_url}")
print(f"User: {client.auth.login}")
```

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

## Configuration

Before creating a client, set up your configuration file at `~/.bfabricpy.yml`:

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

```{note}
    The password in your config file is not your login password. You can find your web service password on your B-Fabric
    profile page.
```

## Creating a Client

### Basic Usage

The simplest way to create a client is to call `Bfabric.connect()` without arguments:

```python
from bfabric import Bfabric

client = Bfabric.connect()
```

This will:

1. Check if the `BFABRICPY_CONFIG_OVERRIDE` environment variable is set (highest priority)
2. If not, use your `~/.bfabricpy.yml` config file
3. Determine the environment by checking:
    - The `BFABRICPY_CONFIG_ENV` environment variable
    - The `default_config` value in your config file (e.g., "PRODUCTION")
4. Create a client with authentication from the config

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

client = Bfabric.connect()

# Temporarily use different credentials
with client.with_auth(BfabricAuth(login="other_user", password="other_pass")):
    # All operations in this block use different authentication
    samples = client.read(endpoint="sample", obj={"name": "Test"})

# Authentication is restored after the block
samples = client.read(endpoint="sample", obj={"name": "Test"})

print(f"Current user: {client.auth.login}")  # Shows original user
```

## Configuration Priority

Configuration is loaded in the following order (highest priority first):

1. **Environment variable `BFABRICPY_CONFIG_OVERRIDE`** - If set, this overrides everything else. This is a JSON
    string containing the full configuration data.

2. **Explicit `config_file_env` parameter** - When calling `Bfabric.connect()`, this takes precedence over
    environment variables.

3. **Environment variable `BFABRICPY_CONFIG_ENV`** - Sets the default environment when `config_file_env="default"`.

4. **`default_config` in config file** - Fallback if none of the above are set.

### Config Override Example

You can override all configuration by setting the `BFABRICPY_CONFIG_OVERRIDE` environment variable with a JSON string:

```bash
export BFABRICPY_CONFIG_OVERRIDE='{"client": {"base_url": "https://fgcz-bfabric.uzh.ch/bfabric/"}, "auth": {"login": "myuser", "password": "mypass"}}'
```

This is useful in containerized environments or when you don't want to use a config file.

### Config File Selection Logic

When using the config file (no override), the environment is selected as follows:

1. If `config_file_env` is provided explicitly to `Bfabric.connect()`, use that
2. If `config_file_env` is `"default"`:
    - Check `BFABRICPY_CONFIG_ENV` environment variable
    - If not set, use `default_config` from the `GENERAL` section of the config file
3. If `config_file_env` is `None`, no config file will be used (error unless override is present)

## Creating a Client Without Authentication

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

## Environment Variable Examples

### Setting the Default Environment

```bash
# Set which config environment to use by default
export BFABRICPY_CONFIG_ENV=TEST

python my_script.py  # Will use TEST environment by default
```

### Providing Full Configuration via Environment

```bash
# Complete configuration override (highest priority)
export BFABRICPY_CONFIG_OVERRIDE='{"client": {"base_url": "https://fgcz-bfabric.uzh.ch/bfabric/"}, "auth": {"login": "myuser", "password": "mypass"}}'

python my_script.py  # Will use this config, ignoring ~/.bfabricpy.yml
```

## Verification

Always verify you're using the correct environment:

```python
from bfabric import Bfabric

client = Bfabric.connect()
print(f"Connected to: {client.config.base_url}")
print(f"User: {client.auth.login}")
```

## Server/Webapp Usage?

If you're building a web server or application that receives B-Fabric tokens from web apps, see
{doc}`client_server` for information on token-based authentication.

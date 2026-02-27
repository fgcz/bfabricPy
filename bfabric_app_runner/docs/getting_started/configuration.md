# Configuration

bfabric-app-runner uses the same B-Fabric credential configuration as the bfabric core library. This guide covers how to configure your B-Fabric credentials for use with bfabric-app-runner.

## B-Fabric Credential Configuration

bfabric-app-runner authenticates with B-Fabric using credentials stored in a configuration file or environment variables. This allows you to:

- Switch between different B-Fabric instances (PRODUCTION vs TEST)
- Share credentials across bfabric tools
- Use environment-specific configurations

## Configuration File Location

bfabric-app-runner looks for a configuration file at:

```
~/.bfabricpy.yml
```

## Configuration File Structure

Create or edit `~/.bfabricpy.yml` with the following structure:

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

### Configuration Elements

| Element | Description |
| ---------------- | ------------------------------------------------------------------------ |
| **GENERAL** | Global configuration settings |
| **default_config** | Default environment to use when not specified (e.g., "PRODUCTION") |
| **PRODUCTION** | Configuration for the production B-Fabric instance |
| **TEST** | Configuration for the test B-Fabric instance |
| **login** | Your B-Fabric username |
| **password** | Your B-Fabric web service password (not login password) |
| **base_url** | B-Fabric instance URL |

```{important}
The `password` in your config file is your **web service password**, not your B-Fabric login password. You can find your web service password on your B-Fabric profile page.
```

## Finding Your Web Service Password

1. Log in to B-Fabric (e.g., https://fgcz-bfabric.uzh.ch/bfabric/)
2. Navigate to your profile page
3. Look for the "Web Service Password" or "Password for Web Service" section
4. Copy this password to use in your configuration file

## Using Different Environments

### Default Environment

bfabric-app-runner will use the environment specified by `default_config` in the GENERAL section:

```yaml
GENERAL:
  default_config: PRODUCTION  # Will use PRODUCTION by default
```

```bash
bfabric-app-runner run workunit app_spec.yml 12345
# Uses PRODUCTION environment
```

### Specifying Environment via Environment Variable

You can override the default environment using the `BFABRICPY_CONFIG_ENV` environment variable:

```bash
# Use TEST environment
export BFABRICPY_CONFIG_ENV=TEST
bfabric-app-runner run workunit app_spec.yml 12345
```

### Multiple Environments

You can configure as many environments as needed:

```yaml
GENERAL:
  default_config: PRODUCTION

PRODUCTION:
  login: myuser
  password: mypassword
  base_url: https://fgcz-bfabric.uzh.ch/bfabric/

TEST:
  login: myuser
  password: mypassword
  base_url: https://fgcz-bfabric-test.uzh.ch/bfabric/

DEVELOPMENT:
  login: myuser
  password: mypassword
  base_url: https://fgcz-bfabric-dev.uzh.ch/bfabric/
```

## Configuration Override (Advanced)

For advanced use cases (e.g., containerized environments), you can override the entire configuration using the `BFABRICPY_CONFIG_OVERRIDE` environment variable with a JSON string:

```bash
export BFABRICPY_CONFIG_OVERRIDE='{"client": {"base_url": "https://fgcz-bfabric.uzh.ch/bfabric/"}, "auth": {"login": "myuser", "password": "mypass"}}'
```

This is the **highest priority** configuration method and overrides everything else.

## Configuration Priority

Configuration is loaded in the following order (highest priority first):

1. **Environment variable `BFABRICPY_CONFIG_OVERRIDE`** - JSON string with full configuration
2. **Environment variable `BFABRICPY_CONFIG_ENV`** - Specifies which environment to use
3. **`default_config` in config file** - Fallback environment

## Verifying Your Configuration

Test that your configuration is working correctly:

```bash
# Test with bfabric-cli (part of bfabric package)
bfabric-cli --version

# Test B-Fabric connection
bfabric-cli api read workunit --limit 1
```

If successful, you should see output showing workunit data from B-Fabric.

## Best Practices

### Use Separate Environments

Always use the TEST environment for development and testing:

```bash
export BFABRICPY_CONFIG_ENV=TEST
bfabric-app-runner prepare workunit test_workunit.yml
```

### Protect Your Configuration File

Ensure your configuration file has restricted permissions:

```bash
chmod 600 ~/.bfabricpy.yml
```

### Version Control Warning

**Never commit your configuration file to version control**. Add it to `.gitignore`:

```bash
echo "~/.bfabricpy.yml" >> ~/.gitignore_global
```

### Use Environment Variables in CI/CD

For CI/CD pipelines, use environment variables instead of a configuration file:

```bash
# GitHub Actions example
export BFABRICPY_CONFIG_OVERRIDE='{"client": {"base_url": "'"$BFABRIC_URL"'"}, "auth": {"login": "'"$BFABRIC_USER"'", "password": "'"$BFABRIC_PASSWORD"'"}}'
```

## Troubleshooting

### Authentication Failed

**Error**: `Authentication failed` or `Invalid credentials`

**Solution**:

1. Verify your login username is correct
2. Check that you're using your **web service password**, not your login password
3. Ensure you're connecting to the correct B-Fabric instance (PRODUCTION vs TEST)

### Connection Timeout

**Error**: `Connection timeout` or `Could not connect`

**Solution**:

1. Check your network connection
2. Verify the `base_url` is correct
3. Ensure you have VPN access if required (e.g., FGZ network)

### Config File Not Found

**Error**: `Configuration file not found` or `No such file or directory`

**Solution**:

1. Verify the config file exists at `~/.bfabricpy.yml`
2. Check file permissions
3. Ensure the file has correct YAML syntax

### Wrong Environment

**Issue**: bfabric-app-runner is using the wrong B-Fabric instance

**Solution**:

1. Check the `default_config` value in your config file
2. Use `BFABRICPY_CONFIG_ENV` to explicitly specify the environment
3. Verify the `base_url` for each environment

## Related Documentation

- [Installation Guide](installation.md) - Installing bfabric-app-runner and dependencies
- [Quick Start Tutorial](quick_start.md) - Your first bfabric-app-runner workflow
- [Creating a Client (bfabric)](../../bfabric/docs/user_guides/creating_a_client/index.md) - More details on bfabric configuration
- [Troubleshooting](../resources/troubleshooting.md) - Common issues and solutions

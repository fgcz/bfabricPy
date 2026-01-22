# Troubleshooting

Common issues and solutions for getting started with bfabricPy.

## Connection Issues

### Can't connect?

```bash
# Test your configuration
python -c "from bfabric import Bfabric; print(Bfabric.connect().config.base_url)"
```

If this fails, check:

- **Config file exists**:
  - **Linux/macOS**: `~/.bfabricpy.yml` (in your home directory)
  - **Windows**: `C:\Users\<username>\.bfabricpy.yml`
- **YAML syntax is valid**: Check for proper indentation and no syntax errors
- **Password is correct**:
  - Verify login is correct (case-sensitive)
  - Ensure you're using your **web service password**, not your login password
  - Find web service password: Log into B-Fabric web interface → Go to profile → "Web Service Password"

See [Configuration Guide](configuration.md) for details.

## Configuration Issues

### "Configuration file not found"

Ensure your file is at the correct location:

- **Linux/macOS**: `~/.bfabricpy.yml` (in your home directory)
- **Windows**: `C:\Users\<username>\.bfabricpy.yml`

Check that you haven't named it incorrectly (e.g., `.bfabric.yml` instead of `.bfabricpy.yml`).

### "Invalid login or password"

- Verify login is correct (case-sensitive)
- Ensure you're using your **web service password**, not your login password
- Check that password doesn't contain special characters that need escaping in YAML

### "No default_config found"

Add a `default_config` field under the `GENERAL` section in your config file:

```yaml
# ~/.bfabricpy.yml

GENERAL:
  default_config: PRODUCTION  # Default environment to use

PRODUCTION:
  login: yourBfabricLogin
  password: yourBfabricWebServicePassword
  base_url: https://fgcz-bfabric.uzh.ch/bfabric/
```

## Query Issues

### Query returns no results?

This is usually normal - the filter simply didn't match any records. Try:

1. **Use broader filters**:

   ```python
   results = client.read(endpoint="workunit", obj={}, max_results=10)
   ```

2. **Check filter values**:

   - Are IDs correct?
   - Are names spelled correctly?
   - Are date formats correct? (YYYY-MM-DD)

3. **Use `bfabric-cli api inspect`** to discover valid filters:

   ```bash
   bfabric-cli api inspect workunit
   ```

4. **Check what endpoints are available**:

   ```python
   from bfabric import Bfabric

   client = Bfabric.connect()
   print("Available endpoints:", client.endpoints)
   ```

### Query errors or unexpected results?

Use `bfabric-cli api inspect` to understand what parameters are available:

```bash
# See what parameters an endpoint accepts
bfabric-cli api inspect workunit

# Then build your query with the right parameters
bfabric-cli api read workunit status FINISHED
```

See [API Inspection Guide](api_inspection.md) for complete documentation on using the inspect command.

## Installation Issues

### Python import error

```bash
# Verify installation
python -c "import bfabric; print(bfabric.__version__)"
```

If this fails:

- Check that `bfabric` is installed: `pip list | grep bfabric`
- Try reinstalling: `pip install --force-reinstall bfabric`

### bfabric-cli not found

If you installed `bfabric-scripts`:

```bash
bfabric-cli --version
bfabric-cli --help
```

If this fails:

- Verify installation: `uv tool list | grep bfabric-scripts`
- Reinstall: `uv tool install bfabric-scripts`

## Version Issues

### Wrong B-Fabric instance

Check your configuration is pointing to the correct instance:

```python
from bfabric import Bfabric

client = Bfabric.connect()
print(f"Connected to: {client.config.base_url}")
print(f"User: {client.auth.login}")
```

Common URLs:

- **Production**: `https://fgcz-bfabric.uzh.ch/bfabric/`
- **Test**: `https://fgcz-bfabric-test.uzh.ch/bfabric/`

If you're connecting to the wrong instance, update your config file or use a different environment:

```bash
export BFABRICPY_CONFIG_ENV=TEST  # or PRODUCTION
```

## Getting Help

Still stuck?

1. **Check error messages**: Look at the specific error message for clues
2. **Use API Inspection**: `bfabric-cli api inspect` to understand what you're querying
3. **Review configuration**: Verify all settings are correct
4. **Consult related docs**:
   - [Error Handling](../user_guides/error_handling.md) - Complete error types and handling
   - [API Inspection Guide](api_inspection.md) - Discovering endpoints and parameters
   - [Configuration Guide](configuration.md) - Config file structure

## Common Mistakes

| Mistake | Symptom | Fix |
|----------|-----------|-----|
| Using login password instead of web service password | "Invalid login or password" | Use web service password from B-Fabric profile |
| Config file in wrong location | "Configuration file not found" | Ensure `~/.bfabricpy.yml` (not `.bfabric.yml`) |
| Wrong environment variable | Querying wrong instance | Check `BFABRICPY_CONFIG_ENV` value |
| Missing default_config | "No default_config found" | Add `default_config` field under `GENERAL` section |
| Typos in filter names | No results or errors | Use `bfabric-cli api inspect` to check valid parameter names |

## Next Steps

Once you've resolved the issue:

1. **Test your setup**:

   ```bash
   python -c "from bfabric import Bfabric; print(Bfabric.connect().config.base_url)"
   ```

2. **Try a simple query**:

   ```bash
   bfabric-cli api read workunit --limit 1
   ```

3. **Continue with the tutorials**:

   - [Quick Start](quick_start.md) - Your first script
   - [API Inspection Guide](api_inspection.md) - Exploring the API
   - [Reading Data](../user_guides/reading_data/index.md) - Querying data

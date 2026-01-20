# Quick Start

This guide will help you create your first bfabricPy script in under 5 minutes.

## Step 1: Installation

Install bfabricPy:

```bash
pip install bfabric
```

## Step 2: Configuration

Create a configuration file at `~/.bfabricpy.yml`:

```yaml
# ~/.bfabricpy.yml

GENERAL:
  default_config: PRODUCTION

PRODUCTION:
  login: yourBfabricLogin
  password: yourBfabricWebServicePassword  # NOT your login password
  base_url: https://fgcz-bfabric.uzh.ch/bfabric/
```

```{note}
The password is your **web service password**, not your login password. Find it on your B-Fabric profile page.
```

## Step 3: Your First Script

Create a file `my_first_script.py`:

```python
from bfabric import Bfabric

# Create a client (uses default config)
client = Bfabric.connect()

print(f"Connected to: {client.config.base_url}")

# Query for projects
projects = client.read(endpoint="project", obj={"name": "MyProject"})

if projects.is_success:
    print(f"Found {len(projects)} project(s):")
    for project in projects:
        print(f"  - {project['name']} (ID: {project['id']})")
else:
    print(f"Query failed: {projects.errors}")
```

## Step 4: Run It

```bash
python my_first_script.py
```

You should see output like:

```
Connected to: https://fgcz-bfabric.uzh.ch/bfabric/
Found 1 project(s):
  - MyProject (ID: 123)
```

## What's Next?

Congratulations! You've just created your first bfabricPy script. Now you can:

- 📖 [Learn about creating clients](../user_guides/creating_a_client/index.md)
- 📊 [Learn to read data](../user_guides/reading_data/index.md)
- ✏️ [Learn to write data](../user_guides/writing_data/index.md)
- 🏗️ [Learn about entities](../user_guides/working_with_entities/index.md)

## Troubleshooting

### "ImportError: No module named 'bfabric'"

```bash
# Install bfabric
pip install bfabric
```

### "BfabricConfigError"

- Verify your config file at `~/.bfabricpy.yml` exists
- Check YAML syntax (use https://www.yamllint.com/)
- Verify password is your web service password, not login password

### "ValueError: Invalid Entity URI"

- Make sure you're connected to the correct B-Fabric instance
- Check your `base_url` in config file

## See Also

- [Installation Guide](installation.md) - More installation options
- [Configuration Guide](configuration.md) - Advanced configuration options

# Quick Start

This 5-minute tutorial will get you started with bfabricPy by writing your first script.

## Prerequisites

Before starting, make sure you have:

1. **Installed bfabricPy**: Follow [Installation Guide](installation.md)
2. **Configured credentials**: Follow [Configuration Guide](configuration.md)

______________________________________________________________________

## Your First Script

Create a file called `my_first_script.py`:

```python
from bfabric import Bfabric

# Connect to B-Fabric (uses your config file)
client = Bfabric.connect()

print(f"Connected to: {client.config.base_url}")

# Query for recent workunits
results = client.read(endpoint="workunit", obj={}, max_results=5)

print(f"\nFound {len(results)} recent workunit(s):")
for workunit in results:
    print(f"  - ID: {workunit['id']}, Status: {workunit.get('status', 'N/A')}")
```

**Run it:**

```bash
python my_first_script.py
```

**Expected output:**

```
Connected to: https://fgcz-bfabric-test.uzh.ch/bfabric

Found 5 recent workunit(s):
  - ID: 321802, Status: FINISHED
  - ID: 321801, Status: FINISHED
  - ID: 321800, Status: FAILED
  - ID: 321799, Status: RUNNING
  - ID: 321798, Status: FINISHED
```

______________________________________________________________________

## What Just Happened?

Let's break down the script:

```python
from bfabric import Bfabric
```

Import the main Bfabric class.

```python
client = Bfabric.connect()
```

Create a client using your configuration from `~/.bfabricpy.yml`.

```python
results = client.read(endpoint="workunit", obj={}, max_results=5)
```

Query B-Fabric for workunits. Returns a `ResultContainer` object.

```python
for workunit in results:
    print(workunit)
```

Iterate over results like a list.

**Note:** By default, queries raise an error automatically if they fail. See [Error Handling](../user_guides/error_handling.md) to learn about error handling options.

______________________________________________________________________

## Explore the API

Use `bfabric-cli api inspect` to discover available endpoints, parameters, and data structures:

```bash
bfabric-cli api inspect resource
bfabric-cli api inspect workunit
bfabric-cli api inspect dataset
```

See [API Inspection Guide](../user_guides/bfabric-cli/api_inspection) for complete documentation on using the inspect command.

______________________________________________________________________

## What's Next?

Now that you've seen the basics, explore further:

| Want to... | Read this guide |
| ------------------------------------- | ---------------------------------------------------------------------- |
| Understand client authentication | [Creating a Client](../user_guides/creating_a_client/index.md) |
| Query and retrieve data efficiently | [Reading Data](../user_guides/reading_data/index.md) |
| Create, update, delete entities | [Writing Data](../user_guides/writing_data/index) |
| Use typed entities with relationships | [Working with Entities](../user_guides/working_with_entities/index) |
| Explore API endpoints | [API Inspection Guide](../user_guides/bfabric-cli/api_inspection) |

## See Also

- [Installation Guide](installation) - Installation options
- [Configuration Guide](configuration) - Config file structure and options
- [API Inspection Guide](../user_guides/bfabric-cli/api_inspection) - Discovering API endpoints and parameters
- [Creating a Client](../user_guides/creating_a_client/index) - Authentication methods
- [Troubleshooting](troubleshooting) - Common issues and solutions

# API Inspection with CLI

Use `bfabric-cli api inspect` to discover available endpoints, parameters, and data structures in B-Fabric.

## Overview

The `inspect` command helps you:

- **Discover what entities exist** - Browse all available B-Fabric endpoints
- **Learn valid filters** - See what parameters you can use in queries
- **Understand field types** - Know what data types are expected (string, integer, date, etc.)
- **Find required fields** - Required parameters are marked with `*`

## Basic Usage

```bash
# Inspect an endpoint's structure
bfabric-cli api inspect resource

# Inspect different methods
bfabric-cli api inspect resource save

# Check multiple endpoints
bfabric-cli api inspect workunit
bfabric-cli api inspect dataset
bfabric-cli api inspect sample
```

**Output:**

```
Namespaces:
  bf: http://endpoint.server.webservice.bfabric.org/
  xs: http://www.w3.org/2001/XMLSchema

Parameter: parameters
Type: xmlRequestReadResource
  - idonly: xs:string
  - login: xs:string *
  - password: xs:string *
  - page: xs:int
  - query: bf:xmlRequestParameterReadResource
    - id: xs:long[]
    - name: xs:string[]
    - createdby: xs:string[]
    - createdafter: xs:string[]
    - createdbefore: xs:string[]
    - containerid: xs:long[]
    sampleid: xs:long[]
    status: xs:string[]
    size: xs:long[]
    - ...more fields

* required
```

## Common Patterns

### Inspect Different Methods

```bash
# See what 'read' expects (default method)
bfabric-cli api inspect resource

# See what 'save' expects (for creating/updating)
bfabric-cli api inspect resource save

# Check workunit structure
bfabric-cli api inspect workunit

# Check dataset structure
bfabric-cli api inspect dataset

# Check sample structure
bfabric-cli api inspect sample
```

### Discover Available Endpoints

```bash
# Common B-Fabric endpoints to inspect:
bfabric-cli api inspect sample
bfabric-cli api inspect workunit
bfabric-cli api inspect dataset
bfabric-cli api inspect resource
bfabric-cli api inspect application
bfabric-cli api inspect project
```

## Practical Examples

### Example 1: Filter by Date

First, inspect to see available date filters:

```bash
bfabric-cli api inspect resource
```

From output, you can see `createdafter` and `createdbefore` are valid filters. Use them in Python:

```python
from bfabric import Bfabric
from datetime import datetime, timedelta

client = Bfabric.connect()

# Find resources created in last 30 days
date_threshold = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

results = client.read(
    endpoint="resource",
    obj={"createdafter": date_threshold},
    max_results=10,
)

if results.is_success:
    print(f"Found {len(results)} recent resources:")
    for resource in results:
        print(f"  - {resource['name']} (ID: {resource['id']})")
```

### Example 2: Filter by User

Inspect to see what user-related filters exist:

```bash
bfabric-cli api inspect workunit
```

If you see `createdby` or `modifiedby`, use them:

```python
from bfabric import Bfabric

client = Bfabric.connect()

# Find workunits created by specific user
results = client.read(
    endpoint="workunit",
    obj={"createdby": "pfeeder"},
    max_results=10,
)

for workunit in results:
    print(f"  - ID: {workunit['id']}, Status: {workunit.get('status', 'N/A')}")
```

### Example 3: Create New Entity

To create an entity, first inspect the `save` method:

```bash
bfabric-cli api inspect sample save
```

This shows required fields and expected types:

```python
from bfabric import Bfabric

client = Bfabric.connect()

# Create a new sample (required fields from inspect)
sample_data = {
    "name": "Test Sample",
    "projectid": 300,
    "type": "Biological Sample - Generic",
}

results = client.save(endpoint="sample", obj=sample_data)

if results.is_success:
    print(f"Created sample ID: {results[0]['id']}")
else:
    print(f"Errors: {results.errors}")
```

## Tips and Best Practices

1. **Inspect before querying** - Saves trial and error
2. **Check field types** - Know if a field is string, integer, list, etc.
3. **Look for `*` marks** - These are required fields
4. **Explore multiple endpoints** - You might find better ways to query data
5. **Use CLI for quick testing** - Test queries from CLI before coding them

## Integration with CLI

The `inspect` command integrates well with other CLI commands:

```bash
# 1. Inspect structure first
bfabric-cli api inspect sample

# 2. Test query with CLI
bfabric-cli api read sample projectid 123 --limit 5

# 3. Use in your Python script
from bfabric import Bfabric
client = Bfabric.connect()
results = client.read(endpoint='sample', obj={'projectid': 123}, max_results=5)
```

**Tip:** CLI queries display equivalent Python code, making it easy to test and adapt for your scripts.

## See Also

- [CLI Reference](../user_guides/cli_reference/index.md) - Complete CLI documentation
- [Quick Start](quick_start.md) - 5-minute tutorial
- [Reading Data](../user_guides/reading_data/index.md) - Querying B-Fabric

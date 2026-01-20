# Quick Start

This 5-minute tutorial will get you started with bfabricPy by writing your first script.

## Prerequisites

Before starting, make sure you have:

1. **Installed bfabricPy**: Follow the [Installation Guide](installation.md)
2. **Configured credentials**: Follow the [Configuration Guide](configuration.md)

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

if results.is_success:
    print(f"\nFound {len(results)} recent workunit(s):")
    for workunit in results:
        print(f"  - ID: {workunit['id']}, Status: {workunit.get('status', 'N/A')}")
else:
    print(f"Query failed: {results.errors}")
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
if results.is_success:
    pass
```

Check if the query succeeded.

```python
for workunit in results:
    print(workunit)
```

Iterate over the results like a list.

______________________________________________________________________

## Explore the API

New to the API? Use `bfabric-cli inspect` to discover what's available:

**See available endpoints:**

```bash
bfabric-cli api inspect resource
```

This shows the `read` method's structure for resources:

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
    - includeassociations: xs:boolean
    - includedeletableupdateable: xs:boolean
    - fulldetails: xs:boolean
    - createdafter: xs:string[]
    - createdbefore: xs:string[]
    - createdby: xs:string[]
    - modifiedafter: xs:string[]
    - modifiedbefore: xs:string[]
    - modifiedby: xs:string[]
    - name: xs:string[]
    - containerid: xs:long[]
    - companyid: xs:long[]
    - departmentid: xs:long[]
    - instituteid: xs:long[]
    - organizationid: xs:long[]
    - applicationid: xs:long[]
    - archiveexpirationdate: xs:string[]
    - archiveexpirationdateafter: xs:string[]
    - archiveexpirationdatebefore: xs:string[]
    - description: xs:string[]
    - expirationdate: xs:string[]
    - expirationdateafter: xs:string[]
    - expirationdatebefore: xs:string[]
    - filechecksum: xs:string[]
    - inputresourceid: xs:long[]
    - relativepath: xs:string[]
    - report: xs:string[]
    - sampleid: xs:long[]
    - status: xs:string[]
    - storageid: xs:long[]
    - workunitid: xs:long[]
    - size: xs:long[]

* required
```

**Inspect different methods:**

```bash
# See what 'save' expects (for creating/updating)
bfabric-cli api inspect resource save

# Check workunit structure
bfabric-cli api inspect workunit

# Check dataset structure
bfabric-cli api inspect dataset
```

**Why this matters:**

- **Discover what entities exist**: Not sure what to query? Inspect different endpoints
- **Learn valid filters**: See what parameters you can use in queries
- **Understand field types**: Know what data types are expected (string, integer, date, etc.)
- **Required fields**: Required parameters are marked with `*`

**Tip**: Use `inspect` before writing complex queries - it saves trial and error!

______________________________________________________________________

## Try Something More

Now let's build a more complex query. First, use `inspect` to see what filters are available:

```bash
bfabric-cli api inspect resource
```

Based on what you see, you know `createdby`, `createdafter`, `createdbefore` are valid filters. Let's use them:

```python
from bfabric import Bfabric

client = Bfabric.connect()

# Find resources created by 'pfeeder' in the last month
from datetime import datetime, timedelta

date_threshold = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

results = client.read(
    endpoint="resource",
    obj={"createdby": "pfeeder", "createdafter": date_threshold},
    max_results=10,
)

if results.is_success:
    print(f"Found {len(results)} resource(s):")
    for resource in results:
        print(f"  - {resource['name']} (ID: {resource['id']})")
```

______________________________________________________________________

## Try the CLI

For quick one-off tasks, the command-line interface can be faster:

```bash
# Find workunits
bfabric-cli api read workunit --limit 5

# Find resources by user
bfabric-cli api read resource createdby pfeeder --limit 10

# Export to JSON
bfabric-cli api read dataset --format json --file datasets.json

# Inspect before querying (very useful!)
bfabric-cli api inspect sample
bfabric-cli api inspect dataset save
```

See the [CLI Reference](../user_guides/cli_reference/index.md) for more.

______________________________________________________________________

## What's Next?

Now that you've seen the basics, explore further:

| Want to...                            | Read this guide                                                        |
| ------------------------------------- | ---------------------------------------------------------------------- |
| Understand client authentication      | [Creating a Client](../user_guides/creating_a_client/index.md)         |
| Query and retrieve data efficiently   | [Reading Data](../user_guides/reading_data/index.md)                   |
| Create, update, delete entities       | [Writing Data](../user_guides/writing_data/index.md)                   |
| Use typed entities with relationships | [Working with Entities](../user_guides/working_with_entities/index.md) |
| Quick tasks without Python            | [CLI Reference](../user_guides/cli_reference/index.md)                 |

______________________________________________________________________

## Troubleshooting

### Can't connect?

```bash
# Test your configuration
python -c "from bfabric import Bfabric; print(Bfabric.connect().config.base_url)"
```

If this fails, check:

- Config file exists: `~/.bfabricpy.yml`
- YAML syntax is valid
- Password is your **web service password**, not login password

See [Configuration Guide](configuration.md) for details.

### Query returns no results?

```python
# Try a broader query with no filters
results = client.read(endpoint="workunit", obj={}, max_results=10)

# Or query all endpoints to see what's available
from bfabric import Bfabric

client = Bfabric.connect()
print("Available endpoints:", client.endpoints)
```

### Want to see what you're querying?

Use the CLI to explore, then copy the Python code it shows:

```bash
# Quick exploration
bfabric-cli api read workunit --limit 5

# Shows equivalent Python code:
# results = client.read(endpoint='workunit', obj={}, max_results=100)
```

**Or inspect the structure first:**

```bash
# See what parameters workunit accepts
bfabric-cli api inspect workunit

# Then build your query with the right parameters
bfabric-cli api read workunit status FINISHED
```

______________________________________________________________________

## See Also

- [Installation Guide](installation.md) - Installation options and troubleshooting
- [Configuration Guide](configuration.md) - Config file structure and options
- [Creating a Client](../user_guides/creating_a_client/index.md) - Authentication methods

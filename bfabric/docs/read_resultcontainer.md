# ResultContainer API

The `ResultContainer` API provides direct access to B-Fabric data through dictionary-based structures. This is ideal for simple queries,
data analysis, and when you don't need entity relationships.

## Overview

The `ResultContainer` class wraps query results from `client.read()`, providing convenient methods for accessing, converting, and
exporting data.

## Reading Data

### Basic Query

Use `client.read()` to query an endpoint and get a `ResultContainer`:

```python
from bfabric import Bfabric

client = Bfabric.connect()

# Query for samples with a specific name
results = client.read(endpoint="sample", obj={"name": "MySample"}, max_results=100)
```

### Query Parameters

The `client.read()` method accepts these parameters:

- **`endpoint`** (str): The B-Fabric endpoint to query (e.g., "sample", "project", "workunit")
- **`obj`** (dict): Query criteria. For each field, you can provide:
    - A single value: `{"name": "MyProject"}`
    - Multiple values: `{"id": [1, 2, 3]}`
- **`max_results`** (int | None): Maximum number of results to return. Defaults to 100. Set to `None` for all results.
- **`offset`** (int): Number of results to skip (for pagination). Defaults to 0.
- **`check`** (bool): Whether to raise an error if the query fails. Defaults to `True`.
- **`return_id_only`** (bool): Return only IDs instead of full data. Defaults to `False`.

### Example Queries

```python
# Query by single field
results = client.read(endpoint="sample", obj={"name": "Test"})

# Query by multiple fields (AND condition)
results = client.read(endpoint="sample", obj={"name": "Test", "projectid": 123})

# Query with multiple values (OR condition)
results = client.read(endpoint="sample", obj={"id": [1, 2, 3, 4]})

# Get only IDs (faster for existence checks)
results = client.read(endpoint="sample", obj={"name": "Test"}, return_id_only=True)
```

## Working with Results

### Accessing Results

`ResultContainer` behaves like a list of dictionaries:

```python
# Get total number of results
print(len(results))

# Access individual results
first_sample = results[0]

# Iterate over results
for result in results:
    print(result["name"])
```

### Error Handling

Check if the query was successful:

```python
if results.is_success:
    print("Query successful")
else:
    print(f"Errors: {results.errors}")
```

Or raise an error if not successful:

```python
results.assert_success()  # Raises RuntimeError if errors occurred
```

### Pagination

The container tracks pagination information:

```python
# Number of pages available from the API
print(f"Total pages: {results.total_pages_api}")
```

## Exporting Results

### to_list_dict()

Convert results to a list of dictionaries:

```python
data = results.to_list_dict()

# Drop empty/None attributes
data_clean = results.to_list_dict(drop_empty=True)
```

### to_polars()

Convert results to a Polars DataFrame:

```python
# Basic conversion
df = results.to_polars()

# Drop empty attributes
df = results.to_polars(drop_empty=True)

# Flatten nested structures (e.g., relationships)
df = results.to_polars(flatten=True)
```

The `flatten=True` option expands nested structures (like references) into separate columns.

## Example: Data Analysis

```python
from bfabric import Bfabric
import polars as pl

client = Bfabric.connect()

# Query samples
results = client.read(endpoint="sample", obj={"projectid": 123}, max_results=1000)

# Convert to DataFrame
df = results.to_polars(drop_empty=True)

# Filter and analyze
filtered = df.filter(pl.col("name").str.contains("control"))
print(filtered)
```

## Example: Checking Existence

```python
from bfabric import Bfabric

client = Bfabric.connect()

# Check if a sample exists
exists = client.exists(endpoint="sample", key="name", value="MySample")

if exists:
    print("Sample exists!")
```

## Comparison to Entity API

If you find yourself needing any of the following, consider using the {doc}`read_entity_api` instead:

- Working with entity objects and their properties
- Navigating relationships (e.g., project → samples)
- Using URIs to reference entities
- Automatic caching of repeated queries
- Maintaining object identity

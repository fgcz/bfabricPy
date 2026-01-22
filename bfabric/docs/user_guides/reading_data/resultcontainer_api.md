# ResultContainer API

The `ResultContainer` API provides direct access to B-Fabric data through dictionary-based structures. This class wraps query results from `client.read()`, providing convenient methods for accessing, converting, and exporting data. It is ideal for simple queries, data analysis, and when you don't need the overhead of entity objects or relationships.

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

```{eval-rst}
.. automethod:: bfabric.Bfabric.read
    :noindex:
```

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

```{warning}
Pagination in the B-Fabric API is sensitive to concurrent changes. If entities are created or deleted while you are paginating through results, you may encounter duplicate or missing entries.

To partially alleviate this, you can add a `createdbefore` parameter to your query to "freeze" the result set to a specific point in time, though even then, deleted entities may still cause issues.
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

For detailed information on handling query errors, see {doc}`../error_handling`.

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

If you find yourself needing any of the following, consider using the {doc}`entity_api` instead:

- Working with entity objects and their properties
- Navigating relationships (e.g., project → samples)
- Using URIs to reference entities
- Automatic caching of repeated queries
- Maintaining object identity

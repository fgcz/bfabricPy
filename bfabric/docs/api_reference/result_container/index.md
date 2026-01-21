# API Reference: ResultContainer

Complete reference for the `ResultContainer` class.

```{eval-rst}
.. autoclass:: bfabric.results.result_container.ResultContainer
    :members:
    :undoc-members:
    :show-inheritance:
```

## Overview

`ResultContainer` is returned by Bfabric read operations and provides:

- **List-like interface**: Iterate over results with indexing
- **Error tracking**: Check if operations succeeded
- **Pagination information**: Total pages available
- **Conversion methods**: Export to various formats

## Quick Examples

### Basic Usage

```python
from bfabric import Bfabric

client = Bfabric.connect()
results = client.read(endpoint="sample", obj={}, max_results=10)

# Check if successful
if results.is_success:
    print("Query successful!")
    for sample in results:
        print(f"  - {sample['name']}")
else:
    print(f"Errors: {results.errors}")
```

### Iteration

```python
# Iterate over results
for result in results:
    print(result["name"])

# Index like a list
first_result = results[0]
first_three = results[0:3]
```

### Length Check

```python
# Get number of results
num_results = len(results)
print(f"Found {num_results} results")
```

### Error Handling

```python
results = client.read(endpoint="sample", obj={"name": "Test"})

# Manual error checking
if not results.is_success:
    for error in results.errors:
        print(f"Error: {error.message}")

# Or use automatic error checking
results = client.read(endpoint="sample", obj={"name": "Test"}, check=True)
```

### Pagination Information

```python
results = client.read(endpoint="sample", obj={})

print(f"Total pages available: {results.total_pages_api}")
```

## See Also

- [ResultContainer API](../../user_guides/reading_data/resultcontainer_api.md) - User guide for ResultContainer
- [Error Handling](../../resources/error_handling.md) - Error types and handling patterns

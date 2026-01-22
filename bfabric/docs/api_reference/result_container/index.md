# ResultContainer API Reference

Complete API reference for the `ResultContainer` class.

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
- **Conversion methods**: Export to various formats (list, Polars DataFrame)

## See Also

- [ResultContainer User Guide](../../user_guides/reading_data/resultcontainer_api.md) - Comprehensive guide with examples
- [Error Handling](../../user_guides/error_handling.md) - Error types and handling patterns

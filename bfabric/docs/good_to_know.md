# Good to Know

## Updating workunits with many associated resources

!!! note "Summary: Updating workunits and its associated resources"
    1. Set workunit state to `"processing"`.
    2. Update workunit and associated resources, as much as you need to.
    3. Set workunit state to `"available"`.

When updating large workunits, it's crucial to prevent state recomputation in B-Fabric by setting the workunit state to `"processing"` before making any changes.
Failing to do so can lead to significant performance issues and complications, especially during iterative updates.

After all entities have been saved, you can set the workunit state to `"available"`.
However, be aware that B-Fabric will still perform a state recomputation at this stage, which might result in a different inferred state, such as `"failed"`.
The `"processing"` state is the only one that ensures state recomputation is bypassed during the saving process.

## Logging level

BfabricPy uses [loguru](https://github.com/Delgan/loguru) for logging, since it makes logging very simple and informative.
While it is recommended by its developers to make it opt-in, our logging is opt-out, but this can easily be adjusted as needed.

### In your code

You can configure loguru in your code:

```python
import sys
from loguru import logger

# Configure a logger with custom settings (requires first removing the default logger)
logger.remove()
logger.add(sys.stderr, filter="bfabric", level="WARNING", colorize=False)

# Alternative: completely deactivate logs for bfabricPy
logger.disable("bfabric")
```

Check the documentation for [logger.add](https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.add) for more options.
By default, the logs go to standard error, which can be useful in some scenarios.

Alternatively, you can set the environment variable `LOGURU_LEVEL`, e.g. `LOGURU_LEVEL=WARNING`. However, this will affect all loguru loggers in your code and may thus not be the preferable approach.

### In bfabricPy scripts

Generally, to achieve a consistent output in our scripts, we initialize the logger by the following function:

```python
from bfabric.utils.cli_integration import setup_script_logging

setup_script_logging()
```

This removes time stamps and line numbers, unless the environment variable `BFABRICPY_DEBUG` is set.

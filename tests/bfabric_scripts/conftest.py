import os

import pytest


@pytest.fixture(autouse=True)
def _reset_script_logging() -> None:
    """Reset the one-shot script-logging guard so log assertions are order-independent.

    ``bfabric.utils.cli_integration.setup_script_logging`` configures the loguru sink only
    once per process, guarded by the ``BFABRICPY_SCRIPT_LOGGING_SETUP`` env var. In a pytest
    process that runs many ``@use_client`` commands the sink stays bound to whichever test
    triggered setup first, so ``capfd``-based log assertions depend on test execution order
    (and flake under randomised ordering). Clearing the flag around every test forces a fresh
    setup bound to the current capture.
    """
    os.environ.pop("BFABRICPY_SCRIPT_LOGGING_SETUP", None)
    yield
    os.environ.pop("BFABRICPY_SCRIPT_LOGGING_SETUP", None)

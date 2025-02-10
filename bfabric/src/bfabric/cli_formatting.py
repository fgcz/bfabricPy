import warnings

from bfabric.utils.cli_integration import setup_script_logging

warnings.warn("This module is a compat-shim and will be deleted soon", DeprecationWarning)

_ = setup_script_logging

"""Login / OAuth CLI commands."""

from __future__ import annotations

from pathlib import Path

# Module-level constant so it is not constructed inside a parameter default
# expression (see reportCallInDefaultInitializer).
DEFAULT_CONFIG_FILE = Path("~/.bfabricpy.yml")

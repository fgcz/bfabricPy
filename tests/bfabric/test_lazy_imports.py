import subprocess
import sys
from pathlib import Path

PROBE = Path(__file__).parent / "_lazy_import_probe.py"


def test_no_module_imports_polars_eagerly() -> None:
    """polars is ~200 MB installed and ~70 ms to import, so nothing may pull it in just to be imported.

    The accessors that return a DataFrame (``HasMany.polars``, ``Dataset.to_polars``,
    ``MultiplexKit.ids``, ``ResultContainer.to_polars``) import it inside the function body instead.
    See ``_lazy_import_probe.EAGER_ALLOWLIST`` for the modules that are exempt because they *are* the
    polars-based features.
    """
    # A subprocess is needed because the pytest process has already imported polars for other tests.
    result = subprocess.run([sys.executable, str(PROBE)], capture_output=True, text=True, check=True)
    offenders = result.stdout.splitlines()
    assert not offenders, "modules importing polars at module scope:\n  " + "\n  ".join(offenders)

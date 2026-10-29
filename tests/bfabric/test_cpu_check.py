import subprocess
import sys


def test_polars_missing_cpu_features_warning_raises():
    # pytest replaces warning filters per test, so check the real import in a fresh interpreter;
    # the message mimics polars' _cpu_check, emitted right before the process dies with SIGILL
    code = "import bfabric, warnings; warnings.warn('Missing required CPU features. Install polars[rtcompat]', RuntimeWarning)"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 1
    assert "RuntimeWarning: Missing required CPU features" in result.stderr

"""Reports every module that imports a heavy dependency at module scope.

Run as a script in a fresh interpreter by ``test_lazy_imports.py`` — it must not run inside pytest,
whose process has already imported polars for other tests. Prints one line per offending import
statement; prints nothing when the package is clean.
"""

import importlib
import importlib.util
import pathlib
import sys

BLOCKED = "polars"

# Modules that may import it eagerly: these are the polars-based features themselves, and none of them
# is reachable from `import bfabric`. Extend only after confirming the module really cannot be reached
# by an `import bfabric` that never asks for a DataFrame.
EAGER_ALLOWLIST = ("bfabric.operations.dataset", "bfabric.utils.polars_utils", "bfabric.utils.table_lint")

# Standalone scripts rather than library code, and not all of them import cleanly.
SKIP = ("bfabric.examples",)


class _Blocker:
    """Makes ``import polars`` fail, so an eager import raises instead of quietly succeeding.

    Blocking rather than inspecting ``sys.modules`` is what makes every offender visible: once the real
    module is loaded the first time, later imports hit the cache and can no longer be attributed.
    """

    def find_spec(self, fullname: str, path: object = None, target: object = None) -> None:
        if fullname.split(".")[0] == BLOCKED:
            raise ModuleNotFoundError(f"blocked by {__name__}: {fullname}", name=fullname)
        return None


def _module_names(root: pathlib.Path) -> list[str]:
    """Every module in the package, `bfabric` itself first, without importing anything."""
    names = []
    for path in root.rglob("*.py"):
        parts = path.relative_to(root).with_suffix("").parts
        names.append(".".join((root.name, *(parts[:-1] if parts[-1] == "__init__" else parts))))
    return sorted(names, key=lambda name: (name != root.name, name))


def _offending_site(error: ModuleNotFoundError, root: pathlib.Path) -> str:
    """The deepest frame inside the package, i.e. the module-scope import statement itself."""
    traceback, site = error.__traceback__, "?"
    while traceback:
        filename = traceback.tb_frame.f_code.co_filename
        if filename.startswith(str(root)):
            site = f"{pathlib.Path(filename).relative_to(root.parent)}:{traceback.tb_lineno}"
        traceback = traceback.tb_next
    return site


def main() -> None:
    # find_spec locates the package without executing its __init__, which may itself be an offender.
    spec = importlib.util.find_spec("bfabric")
    assert spec is not None and spec.submodule_search_locations is not None
    root = pathlib.Path(spec.submodule_search_locations[0])

    sys.meta_path.insert(0, _Blocker())
    offenders: dict[str, str] = {}
    for name in _module_names(root):
        if name.startswith(EAGER_ALLOWLIST + SKIP):
            continue
        try:
            importlib.import_module(name)
        except ModuleNotFoundError as error:
            if error.name != BLOCKED:
                continue  # an optional extra is not installed, e.g. transfer
            # Many modules reach the same statement transitively; report each one once.
            offenders.setdefault(_offending_site(error, root), name)
    for site, name in offenders.items():
        print(f"{site}  (reached by `import {name}`)")


if __name__ == "__main__":
    main()

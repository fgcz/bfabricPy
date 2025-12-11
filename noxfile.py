import os
import re
import shutil
import tomllib
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import nox

nox.options.default_venv_backend = "uv"


def _collect_test_deps(package_dirs):
    """
    Collect test dependencies from package pyproject.toml files.

    Filters out self-references to avoid trying to install packages
    that aren't on PyPI yet or that we're installing from wheels.

    Args:
        package_dirs: Iterable of package directory names

    Returns:
        List of test dependency strings
    """
    all_deps = []
    package_names = set(package_dirs)  # e.g., {"bfabric", "bfabric_scripts"}

    for pkg in package_dirs:
        pyproject = Path(pkg) / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
                deps = data.get("project", {}).get("optional-dependencies", {}).get("test", [])

                # Filter out self-references to packages we're testing
                for dep in deps:
                    # Extract package name from dependency spec
                    # Handles: "pkg>=1.0", "pkg[extra]>=1.0", "pkg[extra]", "pkg"
                    dep_name = (
                        dep.split("[")[0]
                        .split(">=")[0]
                        .split("<=")[0]
                        .split("==")[0]
                        .split("!=")[0]
                        .split("<")[0]
                        .split(">")[0]
                        .split(";")[0]
                        .strip()
                    )

                    if dep_name not in package_names:
                        all_deps.append(dep)

    return all_deps


@contextmanager
def chdir(path: Path) -> Generator[None, None, None]:
    """Context manager to change directory."""
    cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


@nox.session(python=["3.11", "3.13"])
@nox.parametrize("resolution", ["highest", "lowest-direct"])
def test_bfabric(session, resolution):
    if resolution == "lowest-direct" and session.python != "3.11":
        session.skip("Only testing lowest-direct on Python 3.11")

    session.install("--resolution", resolution, "./bfabric[test]")
    session.run("uv", "pip", "list")
    session.run("pytest", "--durations=50", "tests/bfabric")


@nox.session(python=["3.11", "3.13"])
@nox.parametrize("resolution", ["highest", "lowest-direct"])
def test_bfabric_scripts(session, resolution):
    if resolution == "lowest-direct" and session.python != "3.11":
        session.skip("Only testing lowest-direct on Python 3.11")

    session.install("--resolution", resolution, "./bfabric_scripts[test]")
    session.run("uv", "pip", "list")
    packages = ["tests/bfabric_scripts", "tests/bfabric_cli"]
    session.run("pytest", "--durations=50", *packages)


@nox.session(python=["3.13"])
@nox.parametrize("resolution", ["highest", "lowest-direct"])
def test_bfabric_app_runner(session, resolution):
    # Both resolutions run for the single Python version
    session.install("--resolution", resolution, "./bfabric_app_runner[test]")
    session.run("uv", "pip", "list")
    session.run("pytest", "--durations=50", "tests/bfabric_app_runner")


@nox.session
def test_py_typed(session):
    """Verify py.typed is properly installed with the package."""
    session.install("./bfabric")
    result = session.run(
        "python",
        "-c",
        "import bfabric, pathlib; p=pathlib.Path(bfabric.__file__).parent/'py.typed'; print(p.exists())",
        silent=True,
        stderr=None,
    )
    if not result or result.strip() != "True":
        session.error("py.typed not found in installed package")


@nox.session(default=False)
def docs(session):
    """Builds documentation for bfabricPy and app-runner and writes to site directory."""
    with TemporaryDirectory() as tmpdir:
        session.install("./bfabric[doc]")
        with chdir("bfabric"):
            session.run("mkdocs", "build", "-d", Path(tmpdir) / "build_bfabricpy")

        session.install("./bfabric_app_runner[doc]")
        session.run(
            "sphinx-build",
            "-M",
            "html",
            "bfabric_app_runner/docs",
            Path(tmpdir) / "build_app_runner",
        )

        target_dir = Path("site")
        if target_dir.exists():
            shutil.rmtree(target_dir)

        shutil.copytree(Path(tmpdir) / "build_bfabricpy", target_dir)
        shutil.copytree(Path(tmpdir) / "build_app_runner" / "html", target_dir / "app_runner")


@nox.session(default=False)
def publish_docs(session):
    """Publish documentation to GitHub Pages by updating gh-pages branch."""
    site_dir = Path("site")
    if not site_dir.exists():
        session.error("Site directory does not exist. Run 'nox -s docs' first.")

    session.install("ghp-import")
    session.run("ghp-import", "--force", "--no-jekyll", "--push", "site")


@nox.session(default=False)
def code_style(session):
    session.install("ruff")
    session.run("ruff", "check", "bfabric")


@nox.session
def licensecheck(session) -> None:
    """Runs the license check."""
    # TODO revert the upper constraint after https://github.com/FHPythonUtils/LicenseCheck/issues/111 is fixed
    session.install("licensecheck<2025")
    session.run("sh", "-c", "cd bfabric && licensecheck")


@nox.session(python="3.13")
@nox.parametrize("package", ["bfabric", "bfabric_scripts", "bfabric_app_runner", "bfabric_fastapi_proxy"])
def basedpyright(session, package):
    # Install the package in editable mode so basedpyright can find it from source
    session.install("-e", f"./{package}")
    session.install("basedpyright>=1.34.0,<1.35.0")
    # Use --venvpath to explicitly point to nox's venv directory, avoiding .venv if it exists
    venv_path = Path(session.virtualenv.location).parent

    # Check if a specific file was passed via posargs
    if session.posargs:
        # User specified specific file(s) to check
        target = session.posargs
    else:
        # Default: check the entire package directory
        target = [package]

    session.run(
        "basedpyright",
        "--venvpath",
        str(venv_path),
        "--baselinefile",
        f".basedpyright/baseline.{package}.json",
        *target,
    )


def verify_changelog_version(session: nox.Session, package_dir: str) -> None:
    """
    Verify that the changelog contains an entry for the current version.

    Args:
        session: The nox session
        package_dir: The package directory to check (e.g., 'bfabric', 'bfabric_scripts')

    Raises:
        nox.CommandFailed: If the changelog doesn't contain the current version
    """
    package_path = Path(package_dir)

    # Read version from pyproject.toml
    try:
        with open(package_path / "pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
            current_version = pyproject["project"]["version"]
    except (FileNotFoundError, KeyError) as e:
        session.error(f"Failed to read version from pyproject.toml: {e}")

    # Read and check changelog
    changelog_path = package_path / "docs" / "changelog.md"
    try:
        changelog_content = changelog_path.read_text()
    except FileNotFoundError:
        session.error(f"Changelog not found at {changelog_path}")

    # Look for version header with escaped brackets
    version_pattern = rf"## \\\[{re.escape(current_version)}\\\]"
    if not re.search(version_pattern, changelog_content):
        session.error(
            f"{changelog_path} does not contain entry for version {current_version}.\n"
            f"Expected to find a section starting with: ## \\[{current_version}\\]"
        )

    session.log(f"✓ {changelog_path} contains entry for version {current_version}")


@nox.session
def check_changelog(session: nox.Session):
    """Check that changelog contains current version for all packages being released."""
    # List of packages to check - could be made configurable
    packages = ["bfabric", "bfabric_scripts", "bfabric_app_runner"]

    for package in packages:
        verify_changelog_version(session, package)


@nox.session
def check_test_inits(session):
    """Fail if __init__.py files exist in tests directory"""
    # Use pathlib to find all __init__.py files in the tests directory
    tests_dir = Path("tests")
    init_files = list(tests_dir.glob("**/__init__.py"))

    if init_files:
        # __init__.py files were found
        session.error("❌ __init__.py files detected in tests directory")
    else:
        # No __init__.py files found
        session.log("✓ No __init__.py files found in tests directory")


@nox.session(python=["3.11", "3.13"], default=False)
def test_distributions(session):
    """
    Test built distributions (wheels) instead of editable installs.

    This session is used in the PR release preview workflow to validate
    that the packages work correctly when installed from distributions.

    Not run by default - only used in release testing.

    Usage:
        nox -s test_distributions-3.11 -- \
            --wheels bfabric/dist/bfabric-1.14.0-py3-none-any.whl \
            --wheels bfabric_scripts/dist/bfabric_scripts-1.13.37-py3-none-any.whl \
            --resolution highest

    The wheels are installed in the order provided, which should match
    dependency order (base packages first).
    """
    # Parse wheel paths and resolution from command line arguments
    wheels = []
    package_test_map = {}
    resolution = "highest"  # default

    args = session.posargs
    i = 0
    while i < len(args):
        if args[i] == "--wheels":
            if i + 1 < len(args):
                wheel_path = args[i + 1]
                wheels.append(wheel_path)

                # Determine which package this wheel belongs to
                if "bfabric_app_runner" in wheel_path:
                    package_test_map["bfabric_app_runner"] = "tests/bfabric_app_runner"
                elif "bfabric_scripts" in wheel_path:
                    package_test_map["bfabric_scripts"] = ["tests/bfabric_scripts", "tests/bfabric_cli"]
                elif "bfabric-" in wheel_path or "/bfabric/" in wheel_path:
                    package_test_map["bfabric"] = "tests/bfabric"
                i += 2
            else:
                session.error("--wheels requires a path argument")
        elif args[i] == "--resolution":
            if i + 1 < len(args):
                resolution = args[i + 1]
                if resolution not in ["highest", "lowest-direct"]:
                    session.error("--resolution must be 'highest' or 'lowest-direct'")
                i += 2
            else:
                session.error("--resolution requires a value (highest or lowest-direct)")
        else:
            i += 1

    if not wheels:
        session.error("No wheels specified. Use: --wheels path/to/wheel.whl --resolution highest")

    session.log(f"Testing with resolution: {resolution}")
    session.log(f"Wheels to test: {wheels}")

    # Collect test dependencies from package pyproject.toml files
    # This automatically filters out self-references and stays in sync
    test_deps = _collect_test_deps(package_test_map.keys())
    session.log(f"Test dependencies: {test_deps}")
    session.install("--resolution", resolution, *test_deps)

    # Install all wheels at once so uv can resolve dependencies between them
    # (installing one at a time causes uv to check PyPI for dependencies)
    session.log(f"Installing wheels: {wheels}")
    session.install(*wheels)

    # Show what's installed for debugging
    session.run("uv", "pip", "list")

    # Run tests for each package that was installed
    for package, test_paths in package_test_map.items():
        session.log(f"Running tests for {package}")
        if isinstance(test_paths, list):
            session.run("pytest", "--durations=50", *test_paths)
        else:
            session.run("pytest", "--durations=50", test_paths)

import os
import re
import shutil
import subprocess
import tomllib
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import nox

nox.options.default_venv_backend = "uv"


def _get_workspace_packages():
    uv_list_paths = subprocess.run(
        ["uv", "workspace", "list", "--paths", "--preview-features", "workspace-list"],
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.splitlines()
    # uv may colorize its output even when piped; strip ANSI escape codes before parsing paths
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    uv_list_paths = [ansi_escape.sub("", p).strip() for p in uv_list_paths]
    uv_list_names = [str(Path(p).relative_to(Path(__file__).parent)) for p in uv_list_paths]
    # exclude the workspace itself
    filtered = set(uv_list_names) - {"."}
    if not filtered:
        raise ValueError("No workspace packages were found")
    return sorted(filtered)


WORKSPACE_PACKAGES = _get_workspace_packages()


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


def _get_python_version_tuple(python_string):
    """
    Parse Python version string to tuple.

    Args:
        python_string: e.g., "3.11" or "3.13"

    Returns:
        tuple like (3, 11)
    """
    parts = python_string.split(".")
    return (int(parts[0]), int(parts[1]))


def _get_package_metadata(package_dir):
    """
    Extract metadata from a package's pyproject.toml.

    Args:
        package_dir: Package directory name (e.g., "bfabric")

    Returns:
        dict with keys:
            - "min_python": tuple like (3, 12) for minimum Python version
            - "test_paths": str or list of test paths
    """
    pyproject_path = Path(package_dir) / "pyproject.toml"

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        raise ValueError(f"pyproject.toml not found for package {package_dir}")

    # Extract requires-python (PEP 621 standard)
    project_data = data.get("project", {})
    requires_python = project_data.get("requires-python")

    if not requires_python:
        raise ValueError(f"No requires-python found in {package_dir}/pyproject.toml")

    # Parse ">=3.12" -> (3, 12)
    match = re.match(r">=(\d+)\.(\d+)", requires_python)
    if not match:
        raise ValueError(f"Unexpected requires-python format in {package_dir}: {requires_python}")

    min_python = (int(match.group(1)), int(match.group(2)))

    # Determine test paths based on package name
    if package_dir == "bfabric":
        test_paths = "tests/bfabric"
    elif package_dir == "bfabric_scripts":
        test_paths = ["tests/bfabric_scripts", "tests/bfabric_cli"]
    elif package_dir == "bfabric_app_runner":
        test_paths = "tests/bfabric_app_runner"
    else:
        # Fallback for unknown packages
        test_paths = f"tests/{package_dir}"

    return {
        "min_python": min_python,
        "test_paths": test_paths,
    }


def _get_package_name_from_wheel(wheel_path):
    """
    Extract package name from wheel filename.

    Args:
        wheel_path: Path to wheel file

    Returns:
        Package name or None if not recognized
    """
    wheel_filename = Path(wheel_path).name

    # Check for known packages - order matters (check longer names first)
    if wheel_filename.startswith("bfabric_app_runner-"):
        return "bfabric_app_runner"
    elif wheel_filename.startswith("bfabric_scripts-"):
        return "bfabric_scripts"
    elif wheel_filename.startswith("bfabric-"):
        return "bfabric"
    else:
        return None


def _filter_compatible_packages(package_names, current_python_tuple):
    """
    Filter packages by Python version compatibility.

    Args:
        package_names: List of package directory names
        current_python_tuple: tuple like (3, 11)

    Returns:
        tuple of (compatible_dict, skipped_list) where:
            - compatible_dict: {package_name: test_paths}
            - skipped_list: [(package_name, min_python_tuple, reason)]
    """
    compatible = {}
    skipped = []

    for pkg in package_names:
        try:
            metadata = _get_package_metadata(pkg)
            min_python = metadata["min_python"]

            if current_python_tuple >= min_python:
                compatible[pkg] = metadata["test_paths"]
            else:
                reason = f"requires Python {min_python[0]}.{min_python[1]}+"
                skipped.append((pkg, min_python, reason))
        except Exception as e:
            # If we can't read metadata, log error and skip
            skipped.append((pkg, None, f"error reading metadata: {e}"))

    return compatible, skipped


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
    session.run("pytest", "--durations=50", "--tb=short", "-ra", "tests/bfabric")


@nox.session(python="3.13")
def test_bfabric_zeep(session):
    """Run the optional zeep-engine tests with the zeep extra installed.

    The default `test_bfabric` session installs `bfabric[test]` without the `zeep`
    extra, so the zeep-engine tests skip there (verifying the no-zeep path). This
    session installs the extra so the engine itself stays covered.
    """
    session.install("./bfabric[test,zeep]")
    session.run("uv", "pip", "list")
    session.run("pytest", "--durations=50", "tests/bfabric/engine/test_engine_zeep.py")


@nox.session(python=["3.11", "3.13"])
@nox.parametrize("resolution", ["highest", "lowest-direct"])
def test_bfabric_scripts(session, resolution):
    if resolution == "lowest-direct" and session.python != "3.11":
        session.skip("Only testing lowest-direct on Python 3.11")

    session.install("--resolution", resolution, "./bfabric_scripts[test]")
    packages = ["tests/bfabric_scripts", "tests/bfabric_cli"]
    session.run("pytest", "--durations=50", "--tb=short", "-ra", *packages)


@nox.session(python=["3.13"])
@nox.parametrize("resolution", ["highest", "lowest-direct"])
def test_bfabric_app_runner(session, resolution):
    # Both resolutions run for the single Python version
    session.install("--resolution", resolution, "./bfabric_app_runner[test]")
    session.run("pytest", "--durations=50", "--tb=short", "-ra", "tests/bfabric_app_runner")


@nox.session(python=["3.13"])
def test_bfabric_asgi_auth(session):
    session.install("--resolution", "highest", "./bfabric_asgi_auth[test]")
    session.run("pytest", "--gherkin-terminal-reporter", "-v", "--tb=short", "bfabric_asgi_auth/tests")


@nox.session(python=["3.13"])
def test_bfabric_rest_proxy(session):
    session.install("--resolution", "highest", "./bfabric_rest_proxy[test]")
    session.run("pytest", "-v", "--tb=short", "bfabric_rest_proxy/tests")


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
    """Builds documentation for bfabricPy and app-runner and writes to site directory.

    Usage:
        nox -s docs                    # builds both
        nox -s docs -- bfabric         # builds only bfabric
        nox -s docs -- bfabric_app_runner  # builds only bfabric_app_runner
    """
    target = session.posargs[0] if session.posargs else None
    valid_targets = {None, "bfabric", "bfabric_app_runner"}

    if target not in valid_targets:
        session.error(f"Invalid target: {target}. Must be one of: bfabric, bfabric_app_runner")

    with TemporaryDirectory() as tmpdir:
        build_bfabricpy = target in (None, "bfabric")
        build_app_runner = target in (None, "bfabric_app_runner")

        if build_bfabricpy:
            session.install("./bfabric[doc]")
            session.run(
                "sphinx-build",
                "-M",
                "html",
                "bfabric/docs",
                Path(tmpdir) / "build_bfabricpy",
            )

        if build_app_runner:
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

        if build_bfabricpy:
            shutil.copytree(Path(tmpdir) / "build_bfabricpy" / "html", target_dir)

        if build_app_runner:
            shutil.copytree(Path(tmpdir) / "build_app_runner" / "html", target_dir / "app_runner")


@nox.session(default=False)
def docs_linkcheck(session):
    """Fails if the docs contain broken internal cross-references.

    Complements ``docs``: MyST only *warns* on unresolvable doc links and missing heading
    anchors, so a plain build stays green while links rot. This session builds both docs
    trees and fails on any cross-reference warning (missing target, ambiguous target, or
    missing local anchor), without being tripped by unrelated warnings.
    """
    session.install("./bfabric[doc]", "./bfabric_app_runner[doc]")
    link_markers = ("xref_missing", "xref_ambiguous", "local id not found")
    problems = []
    for name, srcdir in (("bfabric", "bfabric/docs"), ("bfabric_app_runner", "bfabric_app_runner/docs")):
        with TemporaryDirectory() as tmpdir:
            warnfile = Path(tmpdir) / "warnings.txt"
            session.run("sphinx-build", "-b", "html", "-w", str(warnfile), srcdir, str(Path(tmpdir) / "html"))
            if warnfile.exists():
                problems += [
                    f"{name}: {line}"
                    for line in warnfile.read_text().splitlines()
                    if any(m in line for m in link_markers)
                ]
    if problems:
        session.error("Broken documentation cross-references found:\n" + "\n".join(problems))


@nox.session(default=False)
def code_style(session):
    session.install("ruff")
    session.run("ruff", "check", "bfabric")


@nox.session(python="3.11")
@nox.parametrize("package", WORKSPACE_PACKAGES)
def licensecheck(session, package) -> None:
    """Runs the license check."""
    session.install("licensecheck")
    session.run("licensecheck", "--requirements-paths", f"{package}/pyproject.toml")


@nox.session(python="3.13")
@nox.parametrize("package", WORKSPACE_PACKAGES)
def basedpyright(session, package):
    # Install the package in editable mode so basedpyright can find it from source.
    # bfabric's zeep engine is an optional extra; install it here so its imports
    # (engine_zeep, ResponseDelete.from_zeep, the example scripts) still type-check.
    extras = "[zeep]" if package == "bfabric" else ""
    session.install("-e", f"./{package}{extras}")
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


@nox.session
@nox.parametrize("package", WORKSPACE_PACKAGES)
def changelog(session: nox.Session, package):
    """Verify that the changelog contains an entry for the current version."""
    package_path = Path(package)

    # Read version from pyproject.toml
    try:
        with open(package_path / "pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
            current_version = pyproject["project"]["version"]
    except (FileNotFoundError, KeyError) as e:
        session.error(f"Failed to read version from pyproject.toml: {e}")

    if current_version == "0.0.0":
        session.skip("version 0.0.0 detected")

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

    Automatically filters packages based on Python version compatibility,
    reading requirements from each package's pyproject.toml.

    Not run by default - only used in release testing.

    Usage:
        nox -s test_distributions-3.11 -- \
            --wheels bfabric/dist/bfabric-1.14.0-py3-none-any.whl \
            --wheels bfabric_app_runner/dist/bfabric_app_runner-0.5.0-py3-none-any.whl \
            --resolution highest

    The wheels are installed in the order provided, which should match
    dependency order (base packages first).
    """
    # Parse wheel paths and resolution from command line arguments
    wheels = []
    resolution = "highest"  # default

    args = session.posargs
    i = 0
    while i < len(args):
        if args[i] == "--wheels":
            if i + 1 < len(args):
                wheels.append(args[i + 1])
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

    # Map wheels to package names
    wheel_package_map = {}
    for wheel in wheels:
        pkg_name = _get_package_name_from_wheel(wheel)
        if pkg_name:
            wheel_package_map[wheel] = pkg_name
        else:
            session.warn(f"Could not determine package name from wheel: {wheel}")

    requested_packages = list(wheel_package_map.values())

    # Get current Python version
    current_python = _get_python_version_tuple(session.python)
    session.log(f"Testing with Python {session.python}")
    session.log(f"Resolution strategy: {resolution}")

    # Filter packages by compatibility
    compatible_packages, skipped_packages = _filter_compatible_packages(requested_packages, current_python)

    # Log skipped packages
    if skipped_packages:
        session.log("")
        session.log("Skipped packages (incompatible with current Python):")
        for pkg, min_ver, reason in skipped_packages:
            if min_ver:
                session.log(f"   - {pkg}: {reason} (current: {current_python[0]}.{current_python[1]})")
            else:
                session.log(f"   - {pkg}: {reason}")
        session.log("")

    # Skip (don't fail) if nothing is compatible: a release containing only
    # packages that require a newer Python than this matrix leg is an expected
    # situation, not an error (e.g. a bfabric_app_runner-only release on the
    # 3.11 leg). The leg is left untested, which is safe only as long as some
    # other matrix leg's Python is >= every releasable package's minimum.
    if not compatible_packages:
        session.skip(
            f"No packages are compatible with Python {session.python}. "
            f"Requested packages: {', '.join(requested_packages)}"
        )

    # Log compatible packages
    session.log("Testing compatible packages:")
    for pkg in compatible_packages:
        session.log(f"   - {pkg}")
    session.log("")

    # Filter wheels to only include compatible packages
    compatible_wheels = [wheel for wheel, pkg in wheel_package_map.items() if pkg in compatible_packages]

    session.log(f"Installing wheels: {len(compatible_wheels)}/{len(wheels)}")
    for wheel in compatible_wheels:
        session.log(f"   - {Path(wheel).name}")
    session.log("")

    # Collect test dependencies from compatible packages only
    test_deps = _collect_test_deps(compatible_packages.keys())
    if test_deps:
        session.log(f"Installing test dependencies: {len(test_deps)} packages")
        session.install("--resolution", resolution, *test_deps)

    # Install all compatible wheels at once so uv can resolve dependencies
    session.log("Installing wheels...")
    session.install(*compatible_wheels)

    # Run tests for each compatible package
    for package, test_paths in compatible_packages.items():
        session.log(f"Running tests for {package}...")
        if isinstance(test_paths, list):
            session.run("pytest", "--durations=50", "--tb=short", "-ra", *test_paths)
        else:
            session.run("pytest", "--durations=50", "--tb=short", "-ra", test_paths)
        session.log(f"Tests passed for {package}")
        session.log("")

    session.log("All compatible packages tested successfully!")

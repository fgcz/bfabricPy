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
@nox.parametrize("package", ["bfabric", "bfabric_scripts", "bfabric_app_runner"])
def basedpyright(session, package):
    # Install the package in editable mode so basedpyright can find it from source
    session.install("-e", f"./{package}")
    session.install("basedpyright>=1.34.0,<1.35.0")
    session.run("basedpyright", "--baselinefile", f".basedpyright/baseline.{package}.json", package)


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

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import nox

nox.options.default_venv_backend = "uv"


@nox.session(python=["3.9", "3.13"])
def tests(session):
    session.install(".[test]")
    session.run("uv", "pip", "list")
    session.run("pytest", "tests/bfabric", "tests/bfabric_scripts")


@nox.session(python=["3.13"])
def test_app_runner(session):
    # TODO this one has a problem that bfabric gets installed from `@main` (so it could break CI)
    session.install(".")
    session.install("./app_runner[test]")
    session.run("uv", "pip", "list")
    session.run("pytest", "tests/app_runner")


@nox.session
def test_py_typed(session):
    """Verify py.typed is properly installed with the package."""
    session.install(".")
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
        session.install(".[doc]")
        session.run("mkdocs", "build", "-d", Path(tmpdir) / "build_bfabricpy")

        session.install("./app_runner[doc]")
        session.run("sphinx-build", "-M", "html", "app_runner/docs", Path(tmpdir) / "build_app_runner")

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

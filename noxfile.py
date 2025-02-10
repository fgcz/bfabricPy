import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import nox

# TODO check the problem
nox.options.default_venv_backend = "uv"


@nox.session(python=["3.9", "3.11", "3.13"])
def tests(session):
    session.install("./bfabric[test]", "-e", "./bfabric_scripts")
    session.run("uv", "pip", "list")
    packages = ["tests/bfabric", "tests/bfabric_scripts"]
    if session.python.split(".")[0] == "3" and int(session.python.split(".")[1]) >= 11:
        packages.append("tests/bfabric_cli")
    session.run("pytest", "--durations=50", *packages)


@nox.session(python=["3.13"])
def test_app_runner(session):
    session.install("-e", "./bfabric")
    session.install("./bfabric_app_runner[test]")
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
    # TODO is there a better way
    session.install("licensecheck")
    session.run("sh", "-c", "cd bfabric && licensecheck")

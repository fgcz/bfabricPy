import nox
import shutil
from tempfile import TemporaryDirectory
from pathlib import Path


nox.options.default_venv_backend = "uv"


@nox.session
def tests(session):
    session.install(".[test]")
    session.run("uv", "pip", "list")
    session.run("pytest")


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

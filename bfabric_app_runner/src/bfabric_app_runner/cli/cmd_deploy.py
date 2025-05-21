from pathlib import Path

from bfabric_app_runner.deploy.app_zip import build_app_zip


def cmd_deploy_build_app_zip(
    project_path: Path | None = None,
    output_folder: Path | None = None,
    app_yml_path: Path | None = None,
    allow_dirty: bool = False,
    python_version: str = "3.13",
) -> None:
    """Build an app.zip from the current or specified Python project."""
    if project_path is None:
        project_path = Path.cwd()
    if output_folder is None:
        output_folder = project_path / "app_zip"
    output_folder.mkdir(parents=True, exist_ok=True)

    build_app_zip(
        project_path=project_path,
        output_folder=output_folder,
        app_yml_path=app_yml_path,
        allow_dirty=allow_dirty,
        python_version=python_version,
    )

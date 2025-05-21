import re
import shlex
import subprocess
from functools import cached_property
from pathlib import Path
from zipfile import ZipFile

from loguru import logger


class UvAppZipHelper:
    def __init__(self, project_path: Path) -> None:
        self._project_path = project_path

    @cached_property
    def package_name(self) -> str:
        return re.sub(r"[^\w\d.]+", "_", self._package_name_version[0], re.UNICODE)

    @property
    def version(self) -> str:
        return self._package_name_version[1]

    @cached_property
    def is_dirty(self) -> bool:
        """Checks if the project directory is dirty (contains uncommitted changes)."""
        cmd = ["git", "status", "--porcelain"]
        logger.debug(f"Executing command: {shlex.join(cmd)}")
        result = subprocess.run(cmd, cwd=self._project_path, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to check git status: {result.stderr.strip()}")
        return bool(result.stdout.strip())

    def check_dirty(self, allow_dirty: bool) -> None:
        """Checks if the directory is dirty, printing a message if it is and raising and error if not allowed."""
        if self.is_dirty and not allow_dirty:
            raise RuntimeError("The project directory is dirty. Please commit or stash your changes.")
        elif self.is_dirty:
            logger.warning("The project directory is dirty (uncommitted changes).")

    def build_wheel(self) -> None:
        cmd = ["uv", "build", "--wheel"]
        logger.debug(f"Executing command: {shlex.join(cmd)}")
        subprocess.run(cmd, cwd=self._project_path, check=True)

    @property
    def expected_wheel_path(self) -> Path:
        wheel_dir = self._project_path / "dist"
        file_name = f"{self.package_name}-{self.version}-py3-none-any.whl"
        return wheel_dir / file_name

    def export_pylock_toml(self) -> None:
        cmd = ["uv", "export", "--format", "pylock.toml", "--locked", "-o", "pylock.toml", "--no-emit-project"]
        logger.info(f"Executing command: {shlex.join(cmd)}")
        subprocess.run(cmd, cwd=self._project_path, check=True, text=True, capture_output=True)

    @cached_property
    def _package_name_version(self) -> tuple[str, str]:
        """Returns package name and version by running `uv version` in the project directory."""
        cmd = ["uv", "version"]
        logger.debug(f"Executing command: {shlex.join(cmd)}")
        result = subprocess.run(cmd, cwd=self._project_path, check=True, text=True, capture_output=True)
        [name, version] = result.stdout.strip().split()
        return name, version

    def discover_app_yml(self) -> Path | None:
        candidates = [
            path
            for path in self._project_path.rglob("**/integrations/bfabric/app.yml")
            if ".app_cache" not in path.parts
        ]
        if len(candidates) == 0:
            return None
        elif len(candidates) == 1:
            return candidates[0]
        else:
            msg = f"Multiple app.yml files found. Please specify the correct one: {candidates}"
            raise RuntimeError(msg)


def build_app_zip(
    project_path: Path, output_folder: Path, app_yml_path: Path | None, allow_dirty: bool, python_version: str
) -> None:
    """Builds the app zip requested."""
    helper = UvAppZipHelper(project_path)
    if app_yml_path is None:
        app_yml_path = helper.discover_app_yml()
    helper.check_dirty(allow_dirty=allow_dirty)
    helper.build_wheel()
    helper.export_pylock_toml()
    app_zip_path = output_folder / f"{helper.package_name}-{helper.version}.zip"
    with ZipFile(app_zip_path, "w") as app_zip:
        # Write the app zip version
        app_zip.writestr("app/app_zip_version.txt", "0.1.0")

        # Copy the lockfile
        app_zip.write(project_path / "pylock.toml", arcname="app/pylock.toml")

        # Copy the wheel
        wheel_path = helper.expected_wheel_path
        app_zip.write(wheel_path, arcname=f"app/package/{wheel_path.name}")

        # Copy the app.yml
        app_zip.write(app_yml_path, arcname="app/config/app.yml")

        # Write the python version
        app_zip.writestr("app/python_version.txt", python_version)
    logger.success(f"Successfully created app zip: {app_zip_path}")

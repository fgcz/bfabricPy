from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING, cast

import mako.template
from loguru import logger
from pydantic import BaseModel


if TYPE_CHECKING:
    from bfabric.entities import Workunit


class WrapAppYamlTemplate:
    class Params(BaseModel):
        workunit_id: int
        app_yaml_path: str
        scratch_root: Path
        python_version: str = "3.13"
        """Python version the app_runner itself is launched with (independent of the app's venv).

        Pinned so the runner does not float onto an untested interpreter. See issue #494.
        """

        @classmethod
        def extract_workunit(cls, workunit: Workunit, scratch_root: Path) -> WrapAppYamlTemplate.Params:
            """Reads the app spec path out of the application's executable.

            :raises ValueError: if the executable's ``program`` is not a single path, e.g. because the
                application is registered against the compat wrapper instead of this submitter.
            """
            app_yaml_path = cast("str", workunit.application.executable["program"])
            if any(character.isspace() for character in app_yaml_path):
                # The generated job script reads this as one path, so it used to die on its own first line,
                # long after the submission looked successful.
                msg = (
                    f"The executable of application {workunit.application.id} (workunit {workunit.id}) has a "
                    f"program that is not a single path: {app_yaml_path!r}. This submitter runs the app spec "
                    f"directly, so either register the application against the compat submitter, or set the "
                    f"program to the bare app.yml path. (A path containing whitespace is not supported.)"
                )
                raise ValueError(msg)
            return cls(
                workunit_id=workunit.id,
                app_yaml_path=app_yaml_path,
                scratch_root=scratch_root,
            )

    def __init__(self, params: Params, path: Path) -> None:
        self._params = params
        self._path = path

    @classmethod
    def default_path(cls) -> Path:
        return Path(__file__).parent / "wrap_app_yaml_template.bash.mako"

    def render_string(self) -> str:
        params = self._params.model_dump(mode="python")
        logger.debug("Rendering {} with params: {}", self._path, params)
        template = mako.template.Template(filename=str(self._path))
        return template.render(**params)

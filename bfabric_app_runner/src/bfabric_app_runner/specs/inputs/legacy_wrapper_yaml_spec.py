from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict

from bfabric_app_runner.specs.common_types import RelativeFilePath


class LegacyWrapperYamlSpec(BaseModel):
    """Writes the legacy wrapper-creator YAML for a workunit to a file.

    Compatibility shim for pre-app-runner applications that expect that YAML as their sole argument;
    do not use it for new apps. Nothing is written to B-Fabric, so the YAML carries no external job
    and no ``slurm_stdout``/``slurm_stderr`` log resources -- see the "Running legacy apps" guide.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    type: Literal["legacy_wrapper_yaml"] = "legacy_wrapper_yaml"
    """Discriminator marking this input as a legacy wrapper-creator YAML."""

    filename: RelativeFilePath
    """Target filename (relative to the chunk directory) to write the YAML to."""

    workunit_id: int
    """ID of the workunit to describe."""

    output_path: str
    """Where the app should deposit its output, written to ``application.output``.

    An absolute path inside the chunk directory, so that the app's ``scp`` degrades to a local copy
    and app-runner can register the file afterwards. A ``host:path`` destination is rejected before
    the app runs, since app-runner registers a local file.
    """

    executable: str | None = None
    """``job_configuration.executable``; ``None`` uses the application's own ``program`` field."""

from __future__ import annotations

from pathlib import Path

import cyclopts
import rich
import rich.pretty
import yaml

from app_runner.specs.app.app_spec import AppSpecFile, AppVersions
from app_runner.specs.inputs_spec import InputsSpec
from app_runner.specs.outputs_spec import OutputsSpec
from app_runner.specs.submitter_spec import SubmittersSpec

app_validate = cyclopts.App("validate", help="Validate yaml files.")


@app_validate.command()
def app_spec_file(yaml_file: Path) -> None:
    """Validate an app spec file."""
    app_spec_file = AppSpecFile.model_validate(yaml.safe_load(yaml_file.read_text()))
    rich.pretty.pprint(app_spec_file)


# @app_validate.command()
# def app_spec(yaml_file: Path, interpolate: bool = True, app_id: str = "xxx") -> None:
#    """Validate an app spec file.
#
#    :param yaml_file: Path to the yaml file to validate
#    :param interpolate: Whether to interpolate the app versions or only load the template
#    :param app_id: the app id to use for interpolation
#    """
#    if interpolate:
#        app_versions = AppVersions.load_yaml(yaml_file, app_id=app_id)
#        rich.pretty.pprint(app_versions)
#    else:
#        app_template = AppSpecFile.model_validate(yaml.safe_load(yaml_file.read_text()))
#        rich.pretty.pprint(app_template)


@app_validate.command()
def app_versions(app_yaml: Path, submitters_yaml: Path, app_id: str = "x", app_name: str = "y") -> None:
    """Validates the app versions by expanding the relevant config info."""
    versions = AppVersions.load_yaml(app_yaml, submitters_yaml=submitters_yaml, app_id=app_id, app_name=app_name)
    rich.pretty.pprint(versions)


# @app_validate.command()
# def app_version(app_version: str, app_yaml: Path, submitters_yaml: Path, app_id: str) -> None:
#    """TODO"""
#    app_versions = AppVersions.load_yaml(app_yaml, app_id=app_id)
#    submitters_spec = SubmittersSpec.model_validate(yaml.safe_load(submitters_yaml.read_text()))
#
#    app_version = app_versions.resolve_version(app_version, submitters_spec.submitters)
#    rich.pretty.pprint(app_version)


@app_validate.command()
def inputs_spec(yaml_file: Path) -> None:
    """Validate an inputs spec file."""
    inputs_spec = InputsSpec.model_validate(yaml.safe_load(yaml_file.read_text()))
    rich.pretty.pprint(inputs_spec)


@app_validate.command()
def outputs_spec(yaml_file: Path) -> None:
    """Validate an outputs spec file."""
    outputs_spec = OutputsSpec.model_validate(yaml.safe_load(yaml_file.read_text()))
    rich.pretty.pprint(outputs_spec)


@app_validate.command()
def submitters_spec(yaml_file: Path) -> None:
    """Validate a submitters spec file."""
    submitters_spec = SubmittersSpec.model_validate(yaml.safe_load(yaml_file.read_text()))
    rich.pretty.pprint(submitters_spec)

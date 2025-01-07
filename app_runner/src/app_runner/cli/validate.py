from __future__ import annotations

from pathlib import Path

import cyclopts
import rich
import rich.pretty
import yaml

from app_runner.specs.app.app_spec import AppVersions, AppVersionsTemplate
from app_runner.specs.inputs_spec import InputsSpec
from app_runner.specs.outputs_spec import OutputsSpec

app_validate = cyclopts.App("validate", help="Validate yaml files.")


@app_validate.command()
def app_spec(yaml_file: Path, interpolate: bool = True) -> None:
    """Validate an app spec file.

    :param yaml_file: Path to the yaml file to validate
    :param interpolate: Whether to interpolate the app versions or only load the template
    """
    if interpolate:
        app_versions = AppVersions.load_yaml(yaml_file)
        rich.pretty.pprint(app_versions)
    else:
        app_template = AppVersionsTemplate.model_validate(yaml.safe_load(yaml_file.read_text()))
        rich.pretty.pprint(app_template)


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

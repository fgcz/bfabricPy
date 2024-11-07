from __future__ import annotations

from pathlib import Path

import cyclopts
import rich
import rich.pretty
import yaml

from app_runner.app_runner._spec import AppSpec
from app_runner.input_preparation.spec import InputsSpec
from app_runner.output_registration.spec import OutputsSpec

app_validate = cyclopts.App("validate", help="Validate yaml files.")


@app_validate.command()
def app_spec(yaml_file: Path) -> None:
    """Validate an app spec file."""
    app_spec = AppSpec.model_validate(yaml.safe_load(yaml_file.read_text()))
    rich.pretty.pprint(app_spec)


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

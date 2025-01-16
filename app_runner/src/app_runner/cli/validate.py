from __future__ import annotations

from pathlib import Path

import cyclopts
import yaml
from rich.pretty import pprint

from app_runner.specs.app.app_spec import AppSpecTemplate, AppSpec
from app_runner.specs.inputs_spec import InputsSpec
from app_runner.specs.outputs_spec import OutputsSpec
from app_runner.specs.submitters_spec import SubmittersSpec

app_validate = cyclopts.App("validate", help="Validate yaml files.")


@app_validate.command()
def app_spec_template(yaml_file: Path) -> None:
    """Validate an app spec file."""
    app_spec_file = AppSpecTemplate.model_validate(yaml.safe_load(yaml_file.read_text()))
    pprint(app_spec_file)


@app_validate.command()
def app_spec(app_yaml: Path, app_id: str = "x", app_name: str = "y") -> None:
    """Validates the app versions by expanding the relevant config info."""
    versions = AppSpec.load_yaml(app_yaml, app_id=app_id, app_name=app_name)
    pprint(versions)


@app_validate.command()
def inputs_spec(yaml_file: Path) -> None:
    """Validate an inputs spec file."""
    inputs_spec = InputsSpec.model_validate(yaml.safe_load(yaml_file.read_text()))
    pprint(inputs_spec)


@app_validate.command()
def outputs_spec(yaml_file: Path) -> None:
    """Validate an outputs spec file."""
    outputs_spec = OutputsSpec.model_validate(yaml.safe_load(yaml_file.read_text()))
    pprint(outputs_spec)


@app_validate.command()
def submitters_spec(yaml_file: Path) -> None:
    """Validate a submitters spec file."""
    submitters_spec = SubmittersSpec.model_validate(yaml.safe_load(yaml_file.read_text()))
    pprint(submitters_spec)

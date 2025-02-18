from pathlib import Path

import yaml
from rich.pretty import pprint

from bfabric_app_runner.specs.app.app_spec import AppSpecTemplate, AppSpec
from bfabric_app_runner.specs.inputs_spec import InputsSpec
from bfabric_app_runner.specs.outputs_spec import OutputsSpec
from bfabric_app_runner.specs.submitters_spec import SubmittersSpecTemplate


def cmd_validate_app_spec_template(yaml_file: Path) -> None:
    """Validate an app spec file."""
    app_spec_file = AppSpecTemplate.model_validate(yaml.safe_load(yaml_file.read_text()))
    pprint(app_spec_file)


def cmd_validate_app_spec(app_yaml: Path, app_id: int = 0, app_name: str = "x") -> None:
    """Validates the app versions by expanding the relevant config info."""
    versions = AppSpec.load_yaml(app_yaml, app_id=app_id, app_name=app_name)
    pprint(versions)


def cmd_validate_inputs_spec(yaml_file: Path) -> None:
    """Validate an inputs spec file."""
    inputs_spec = InputsSpec.model_validate(yaml.safe_load(yaml_file.read_text()))
    pprint(inputs_spec)


def cmd_validate_outputs_spec(yaml_file: Path) -> None:
    """Validate an outputs spec file."""
    outputs_spec = OutputsSpec.model_validate(yaml.safe_load(yaml_file.read_text()))
    pprint(outputs_spec)


def cmd_validate_submitters_spec_template(yaml_file: Path) -> None:
    """Validate a submitters spec file."""
    submitters_spec = SubmittersSpecTemplate.model_validate(yaml.safe_load(yaml_file.read_text()))
    pprint(submitters_spec)

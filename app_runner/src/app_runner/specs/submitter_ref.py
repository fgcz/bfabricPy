from typing import Any

from pydantic import BaseModel

from app_runner.specs.submitter_spec import SubmitterSpec


class SubmitterRef(BaseModel):
    """Reference of a submitter and potential configuration overrides."""

    name: str
    config: dict[str, Any] = {}

    def resolve(self, specs: dict[str, SubmitterSpec]) -> SubmitterSpec:
        # TODO move this into a function
        base_spec = specs[self.name]
        base = base_spec.model_dump(mode="json")
        base.update(self.config)
        return type(base_spec).model_validate(base)

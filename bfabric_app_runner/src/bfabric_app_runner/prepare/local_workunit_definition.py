"""TODO this module is experimental and might be better integrated into different modules later."""

from __future__ import annotations

from pydantic import BaseModel, model_validator

from bfabric_app_runner.specs.inputs_spec import LocalInputSpecType  # noqa: TC001


class LocalWorkunitExecutionDefinition(BaseModel):
    """Experimental definition of a local workunit for local execution.

    This is trying to match the structure of WorkunitExecutionRegistration, but, it's notably not compatible right
    now due to the WorkunitExecutionDefinition using IDs instead of full objects (and even less so InputSpecs).
    """

    raw_parameters: dict[str, str | None]
    """The parameters passed to the workunit, in their raw form, i.e. everything is a string or None."""

    dataset: LocalInputSpecType | None = None
    """Input dataset (for dataset-flow applications)"""

    resources: list[LocalInputSpecType] = []
    """Input resources (for resource-flow applications)"""

    @model_validator(mode="after")
    def _mutually_exclusive(self) -> LocalWorkunitExecutionDefinition:
        if (self.dataset is None) == (not self.resources):
            raise ValueError("either dataset or resources must be provided, but not both")
        return self

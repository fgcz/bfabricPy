from pydantic import BaseModel


class WorkflowParams(BaseModel):
    request_failure: bool
    """If set to True, the workflow will fail with an error message (for testing purposes)."""

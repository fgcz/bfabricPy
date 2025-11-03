from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, TypeAdapter, AnyHttpUrl, AfterValidator


def _validate_base_url(value: str) -> str:
    """Validates that the base URL is indeed a valid HTTP URL and ensures it ends with a slash."""
    value = value.rstrip("/") + "/"
    http_url = TypeAdapter(AnyHttpUrl).validate_python(value)
    return str(http_url)


_ValidatedBaseUrl = Annotated[str, AfterValidator(_validate_base_url)]


class BfabricAPIEngineType(str, Enum):
    """Choice of engine to use."""

    SUDS = "SUDS"
    ZEEP = "ZEEP"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


class BfabricClientConfig(BaseModel):
    """Holds the configuration for the B-Fabric client for connecting to particular instance of B-Fabric.

    :param base_url: The API base url
    :param application_ids (optional): Map of application names to ids.
    :param job_notification_emails (optional): Space-separated list of email addresses to notify when a job finishes.
    :param engine: The API engine to use (optional).
    """

    base_url: _ValidatedBaseUrl
    application_ids: Annotated[dict[str, int], Field(default_factory=dict)]
    job_notification_emails: Annotated[str, Field(default="")]
    engine: BfabricAPIEngineType = BfabricAPIEngineType.SUDS

    def copy_with(
        self,
        base_url: str | None = None,
        application_ids: dict[str, int] | None = None,
        engine: BfabricAPIEngineType | None = None,
    ) -> BfabricClientConfig:
        """Returns a copy of the configuration with new values applied, if they are not None."""
        return BfabricClientConfig(
            base_url=base_url if base_url is not None else self.base_url,
            application_ids=(application_ids if application_ids is not None else self.application_ids),
            job_notification_emails=self.job_notification_emails,
            engine=engine if engine is not None else self.engine,
        )

    def __str__(self) -> str:
        return repr(self)

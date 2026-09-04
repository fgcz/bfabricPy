from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from bfabric.config.base_url import BaseUrl


class BfabricAPIEngineType(StrEnum):
    """Choice of engine to use."""

    SUDS = "SUDS"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


class BfabricClientConfig(BaseModel):
    """Holds the configuration for the B-Fabric client for connecting to particular instance of B-Fabric.

    :param application_ids (optional): Map of application names to ids.
    :param job_notification_emails (optional): Space-separated list of email addresses to notify when a job finishes.
    :param engine: The API engine to use (optional).
    """

    base_url: BaseUrl
    application_ids: dict[str, int] = Field(default_factory=dict)
    job_notification_emails: str = ""
    engine: BfabricAPIEngineType = BfabricAPIEngineType.SUDS

    def copy_with(
        self,
        base_url: BaseUrl | None = None,
        application_ids: dict[str, int] | None = None,
    ) -> BfabricClientConfig:
        """Returns a copy of the configuration with new values applied, if they are not None."""
        return BfabricClientConfig(
            base_url=base_url if base_url is not None else self.base_url,
            application_ids=(application_ids if application_ids is not None else self.application_ids),
            job_notification_emails=self.job_notification_emails,
        )

    def __str__(self) -> str:
        return repr(self)

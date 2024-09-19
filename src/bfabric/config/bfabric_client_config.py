from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field, TypeAdapter, AnyHttpUrl

http_url_adapter = TypeAdapter(AnyHttpUrl)


class BfabricClientConfig(BaseModel):
    """Holds the configuration for the B-Fabric client for connecting to particular instance of B-Fabric.

    Parameters:
        base_url (optional): The API base url
        application_ids (optional): Map of application names to ids.
        job_notification_emails (optional): Space-separated list of email addresses to notify when a job finishes.
    """

    # TODO consider using AnyHttpUrl in the future directly and make mandatory
    base_url: Annotated[
        str,
        BeforeValidator(lambda value: str(http_url_adapter.validate_python(value))),
        Field(default="https://fgcz-bfabric.uzh.ch/bfabric"),
    ]
    application_ids: Annotated[dict[str, int], Field(default_factory=dict)]
    job_notification_emails: Annotated[str, Field(default="")]

    def __init__(self, **kwargs) -> None:
        super().__init__(**{key: value for key, value in kwargs.items() if value is not None})

    def copy_with(
        self,
        base_url: str | None = None,
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

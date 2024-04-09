from __future__ import annotations

import io
import json
import logging
import os
from typing import Optional, Dict, Tuple
import dataclasses


@dataclasses.dataclass(frozen=True)
class BfabricAuth:
    """Holds the configuration for authenticating a particular user with B-Fabric."""

    login: str
    password: str

    def __repr__(self):
        return f"BfabricAuth(login={repr(self.login)}, password=...)"

    def __str__(self):
        return repr(self)


@dataclasses.dataclass(frozen=True)
class BfabricConfig:
    """Holds the configuration for the B-Fabric client for connecting to particular instance of B-Fabric.

    Attributes:
        base_url (optional): The API base url
        application_ids (optional): Map of application names to ids.
        job_notification_emails (optional): Space-separated list of email addresses to notify when a job finishes.
    """

    base_url: str = "https://fgcz-bfabric.uzh.ch/bfabric"
    application_ids: Dict[str, int] = dataclasses.field(default_factory=dict)
    job_notification_emails: str = ""

    def with_overrides(
        self,
        base_url: Optional[str] = None,
        application_ids: Optional[Dict[str, int]] = None,
    ) -> BfabricConfig:
        """Returns a copy of the configuration with new values applied, if they are not None."""
        return BfabricConfig(
            base_url=base_url if base_url is not None else self.base_url,
            application_ids=application_ids
            if application_ids is not None
            else self.application_ids,
        )


def parse_bfabricrc_py(file: io.FileIO) -> Tuple[BfabricConfig, Optional[BfabricAuth]]:
    """Parses a .bfabricrc.py file and returns a tuple of BfabricConfig and BfabricAuth objects."""
    values = {}
    file_path = os.path.realpath(file.name)
    logger = logging.getLogger(__name__)
    logger.info(f"Reading configuration from: {file_path}")

    for line in file:
        if line.startswith("#"):
            continue

        key, _, value = [part.strip() for part in line.partition("=")]
        if key not in [
            "_PASSWD",
            "_LOGIN",
            "_WEBBASE",
            "_APPLICATION",
            "_JOB_NOTIFICATION_EMAILS",
        ]:
            continue

        # In case of multiple definitions, the first rule counts!
        if key not in values:
            if key in ["_APPLICATION"]:
                try:
                    values[key] = json.loads(value)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"While reading {file_path}. '{key}' is not a valid JSON string."
                    ) from e
            else:
                # to make it downward compatible; so we replace quotes in login and password
                values[key] = value.replace('"', "").replace("'", "")
        else:
            logger.warning(f"While reading {file_path}. '{key}' is already set.")

    args = dict(
        base_url=values.get("_WEBBASE"),
        application_ids=values.get("_APPLICATION"),
        job_notification_emails=values.get("_JOB_NOTIFICATION_EMAILS"),
    )
    config = BfabricConfig(**{k: v for k, v in args.items() if v is not None})
    if "_LOGIN" in values and "_PASSWD" in values:
        auth = BfabricAuth(login=values["_LOGIN"], password=values["_PASSWD"])
    else:
        auth = None
    return config, auth

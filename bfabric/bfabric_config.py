from __future__ import annotations

import io
import json
import logging
import os
from typing import Optional, Dict


class BfabricConfig:
    """Holds the configuration for the B-Fabric client, and provides methods to load the configuration from a file.

    Attributes:
        login: The username
        password: The web service password (i.e. not the regular user password)
        base_url (optional): The API base url
        application_ids (optional): Map of application names to ids.
    """

    def __init__(
        self,
        login: str,
        password: str,
        base_url: str = None,
        application_ids: Dict[str, int] = None,
    ):
        self.login = login
        self.password = password
        self.base_url = base_url or "https://fgcz-bfabric.uzh.ch/bfabric"
        self.application_ids = application_ids or {}

    def with_overrides(
        self,
        login: Optional[str] = None,
        password: Optional[str] = None,
        base_url: Optional[str] = None,
        application_ids: Optional[Dict[str, int]] = None,
    ) -> BfabricConfig:
        """Returns a copy of the configuration with new values applied, if they are not None."""
        return BfabricConfig(
            login=login if login is not None else self.login,
            password=password if password is not None else self.password,
            base_url=base_url if base_url is not None else self.base_url,
            application_ids=application_ids
            if application_ids is not None
            else self.application_ids,
        )

    @classmethod
    def read_bfabricrc_py(cls, file: io.FileIO) -> BfabricConfig:
        """Reads a .bfabricrc.py file into a BfabricConfig object."""
        values = {}
        file_path = os.path.realpath(file.name)
        logger = logging.getLogger(f"{cls.__module__}.{cls.__name__}")
        logger.info(f"Reading configuration from: {file_path}")

        for line in file:
            if line.startswith("#"):
                continue

            key, _, value = [part.strip() for part in line.partition("=")]
            if key not in ["_PASSWD", "_LOGIN", "_WEBBASE", "_APPLICATION"]:
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

        return BfabricConfig(
            login=values.get("_LOGIN"),
            password=values.get("_PASSWD"),
            base_url=values.get("_WEBBASE"),
            application_ids=values.get("_APPLICATION"),
        )

    def __repr__(self):
        return (
            f"BfabricConfig(login={repr(self.login)}, password=..., base_url={repr(self.base_url)}, "
            f"application_ids={repr(self.application_ids)})"
        )

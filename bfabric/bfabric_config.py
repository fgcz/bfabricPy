from __future__ import annotations

import logging
import os
from typing import Optional, Dict, Tuple, Union
import dataclasses
import yaml
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class BfabricAuth:
    """Holds the configuration for authenticating a particular user with B-Fabric."""

    login: str
    password: str

    def __repr__(self):
        return f"BfabricAuth(login={repr(self.login)}, password=...)"

    def __str__(self):
        return repr(self)


class BfabricConfig:
    """Holds the configuration for the B-Fabric client for connecting to particular instance of B-Fabric.

    Attributes:
        base_url (optional): The API base url
        application_ids (optional): Map of application names to ids.
        job_notification_emails (optional): Space-separated list of email addresses to notify when a job finishes.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        application_ids: Optional[Dict[str, int]] = None,
        job_notification_emails: Optional[str] = None
    ):
        self._base_url = base_url or "https://fgcz-bfabric.uzh.ch/bfabric"
        self._application_ids = application_ids or {}
        self._job_notification_emails = job_notification_emails or ""

    @property
    def base_url(self) -> str:
        """The API base url."""
        return self._base_url

    @property
    def application_ids(self) -> Dict[str, int]:
        """Map of known application names to ids."""
        return self._application_ids

    @property
    def job_notification_emails(self) -> str:
        """Space-separated list of email addresses to notify when a job finishes."""
        return self._job_notification_emails

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

    def __repr__(self):
        return (
            f"BfabricConfig(base_url={repr(self.base_url)}, application_ids={repr(self.application_ids)}, "
            f"job_notification_emails={repr(self.job_notification_emails)})"
        )

def _read_config_env_as_dict(config_path: Union[str, Path], config_env: str = None) -> Tuple[str, dict]:
    """
    Reads and partially parses a bfabricpy.yml file
    :param config_path:  Path to the configuration file. It is assumed that it exists
    :param config_env:   Specific environment to parse. If not provided, it is deduced from an environment variable
       or the config file itself.
    :return: Returns a target environment name, and the corresponding data from bfabricpy.yml file as a dictionary
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Reading configuration from: {config_path}")

    if os.path.splitext(config_path)[1] != '.yml':
        raise IOError(f"Expected config file with .yml extension, got {config_path}")

    # Read the config file
    config_dict = yaml.safe_load(Path(config_path).read_text())

    if "GENERAL" not in config_dict:
        raise IOError("Config file must have a general section")
    if 'default_config' not in config_dict['GENERAL']:
        raise IOError("Config file must provide a default environment")
    config_env_default = config_dict['GENERAL']['default_config']

    # Determine which environment we will use
    # By default, use the one provided by config_env
    if config_env is None:
        # Try to find a relevant
        config_env = os.getenv("BFABRICPY_CONFIG_ENV")
        if config_env is None:
            logger.info(f"BFABRICPY_CONFIG_ENV not found, using default environment {config_env_default}")
            config_env = config_env_default
        else:
            logger.info(f"found BFABRICPY_CONFIG_ENV = {config_env}")
    else:
        logger.info(f"config environment specified explicitly as {config_env}")

    if config_env not in config_dict:
        raise IOError(f"The requested config environment {config_env} is not present in the config file")

    return config_env, config_dict[config_env]

def _have_all_keys(d: dict, l: list) -> bool:
    """True if all elements in list l are present as keys in dict d, otherwise false"""
    return all([k in d for k in l])

def _parse_dict(d: dict, mandatory_keys: list, optional_keys: list = None, error_prefix: str = " ") -> dict:
    """
    Returns a copy of an existing dictionary, only keeping mandatory and optional keys
    If a mandatory key is not found, an exception is raised
    :param d:                 Starting dictionary
    :param mandatory_keys:    A list of mandatory keys
    :param optional_keys:     A list of optional keys
    :param error_prefix:      A string to print if a mandatory key is not found
    :return:                  Copy of a starting dictionary, only containing mandatory and optional keys
    """
    missing_keys = set(mandatory_keys) - set(d)
    if missing_keys:
        raise ValueError(f"{error_prefix}{missing_keys}")
    result_keys = set(mandatory_keys) | set(optional_keys or [])
    d_rez = {k: d[k] for k in result_keys if k in d}

    # Ignore all other fields
    return d_rez

def read_config(config_path: Union[str, Path], config_env: str = None,
                optional_auth: bool = False) -> Tuple[BfabricConfig, Optional[BfabricAuth]]:
    """
    Reads bfabricpy.yml file, parses it, extracting authentication and configuration data
    :param config_path:   Path to the configuration file. It is assumed the file exists
    :param config_env:    Configuration environment to use. If not given, it is deduced.
    :param optional_auth: Whether authentication is optional.
        If not, both login and password must be present in the config file, otherwise an exception is thrown
        If yes, missing login and password would result in authentication class being None, but no exception
    :return: Configuration and Authentication class instances

    NOTE: BFabricPy expects a .bfabricpy.yml of the format, as seen in bfabricPy/tests/unit/example_config.yml
    * The general field always has to be present
    * There may be any number of environments, and they may have arbitrary names. Here, they are called PRODUCTION and TEST
    * Must specify correct login, password and base_url for each environment.
    * application and job_notification_emails fields are optional
    * The default environment will be selected as follows:
        - First, parser will check if the optional argument `config_env` is provided directly to the parser function
        - If not, secondly, the parser will check if the environment variable `BFABRICPY_CONFIG_ENV` is declared
        - If not, finally, the parser will select the default_config specified in [GENERAL] of the .bfabricpy.yml file
    """


    config_env_final, config_dict = _read_config_env_as_dict(config_path, config_env=config_env)

    error_prefix = f"Config environment {config_env_final} does not have a compulsory field: "

    # Parse authentification
    if optional_auth and not _have_all_keys(config_dict, ['login', 'password']):
        # Allow returning None auth if enabled
        auth = None
    else:
        auth_dict = _parse_dict(config_dict, ['login', 'password'], error_prefix=error_prefix)
        auth = BfabricAuth(**auth_dict)

    # Parse config
    config_dict = _parse_dict(config_dict, ['base_url'], optional_keys=['application_ids', 'job_notification_emails'],
                              error_prefix=error_prefix)
    config = BfabricConfig(**config_dict)

    return config, auth

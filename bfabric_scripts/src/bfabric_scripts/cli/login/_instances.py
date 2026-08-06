"""The B-Fabric instances the CLI knows about, for the first-login picker and URL canonicalisation.

Advisory, not restrictive: any base URL is still accepted. Knowing the common ones just means a
first-time user picks from a list instead of finding the URL, a bare host expands to a full base URL,
and a new environment gets a sensible suggested name.

CLI policy, like :data:`DEFAULT_CLIENT_ID` — the core library hardcodes no instances.
"""

from __future__ import annotations

from typing import NamedTuple
from urllib.parse import urlsplit


class Instance(NamedTuple):
    """A known B-Fabric instance: the name suggested for its environment, and its base URL."""

    name: str
    base_url: str


KNOWN_INSTANCES: tuple[Instance, ...] = (
    Instance("fgcz-prod", "https://fgcz-bfabric.uzh.ch/bfabric"),
    Instance("fgcz-test", "https://fgcz-bfabric-test.uzh.ch/bfabric"),
    Instance("fgcz-demo", "https://fgcz-bfabric-demo.uzh.ch/bfabric"),
    Instance("trace", "https://trace.fgcz.uzh.ch/bfabric"),
)


def _host(base_url: str) -> str:
    return urlsplit(base_url if "//" in base_url else f"//{base_url}").netloc.lower()


def match_instance(base_url: str) -> Instance | None:
    """The known instance *base_url* refers to, matched on host alone, or ``None``.

    Host-only matching is what lets a bare ``fgcz-bfabric-demo.uzh.ch`` resolve to a full base URL.
    """
    host = _host(base_url)
    if not host:
        return None
    return next((instance for instance in KNOWN_INSTANCES if _host(instance.base_url) == host), None)


def suggest_env_name(base_url: str) -> str:
    """A default environment name for *base_url*: the known instance's name, else its host.

    Derived rather than prompted for, so a first-time user never has to invent one. Dots become
    dashes because a name is also a YAML key users type on the command line.
    """
    instance = match_instance(base_url)
    if instance is not None:
        return instance.name
    host = _host(base_url)
    return host.replace(".", "-") if host else "bfabric"

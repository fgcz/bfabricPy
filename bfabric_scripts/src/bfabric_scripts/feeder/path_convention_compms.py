from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel
from bfabric.entities import Storage
import re


class ParsedPath(BaseModel):
    absolute_path: Path
    """The absolute path to the file processed."""
    relative_path: Path
    """The path, which was parsed."""
    container_id: int
    """The technology name"""
    technology_name: str
    """The container ID of the resource."""
    application_name: str
    """The application name of the resource."""
    sample_id: int | None
    """If detected, the sample ID to be associated with this resource."""


class PathConventionCompMS:
    """Parses paths according to the CompMS path convention (with slightly relaxed application naming)."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def parse_absolute_path(self, absolute_path: Path) -> ParsedPath:
        relative_path = absolute_path.relative_to(self._storage["basepath"])
        return self.parse_relative_path(relative_path=relative_path)

    def parse_relative_path(self, relative_path: Path) -> ParsedPath:
        """Parses the relative path (to storage root) according to the CompMS path convention."""
        regex = (
            f"{self._storage['projectfolderprefix']}"
            r"(?P<container_id>\d+)/"
            r"(?P<technology>[A-Za-z]+)/"
            r"(?P<application_name>[A-Z_]+_\d+)/"
            r"[a-z]+_\d{8}(?:_[a-zA-Z0-9_]+)/"
            # TODO consider adding sample parsing later (the rule is currently broken)
            # r"[^/]*"
            # r"(?:_\d{3}_S(?P<sample_id>\d+)_.*(?:raw|zip))?"
            r"[^/]*$"
        )
        match = re.match(regex, str(relative_path))
        if not match:
            raise ValueError(f"Path {relative_path} does not match CompMS path convention.")

        container_id = int(match.group("container_id"))
        technology_name = match.group("technology")
        application_name = match.group("application_name")

        return ParsedPath(
            absolute_path=Path(self._storage["basepath"]) / relative_path,
            relative_path=relative_path,
            container_id=container_id,
            technology_name=technology_name,
            application_name=application_name,
            sample_id=None,
        )

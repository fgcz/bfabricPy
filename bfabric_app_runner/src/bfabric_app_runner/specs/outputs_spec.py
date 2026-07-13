from __future__ import annotations

import enum
from pathlib import Path
from typing import Literal, Annotated

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class UpdateExisting(enum.Enum):
    """Policy for what to do when an output with the same identity already exists in B-Fabric.

    Shared by the resource, dataset, and link output specs.
    """

    NO = "no"
    """Never touch an existing entry; fail if one already exists."""

    IF_EXISTS = "if_exists"
    """Update the entry in place if it exists, otherwise create a new one."""

    REQUIRED = "required"
    """Update an existing entry, failing if none exists to update."""


class CopyResourceSpec(BaseModel):
    """Copies a local file into B-Fabric storage and registers it as a resource of the workunit."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_copy_resource"] = "bfabric_copy_resource"

    local_path: Path
    """The local path to the file to be copied."""

    store_entry_path: Path
    """The path to the storage entry in the storage folder."""

    store_folder_path: Path | None = None
    """The storage folder will be determined by the default rule, but can be specified if needed."""

    # TODO these need to be implemented properly (e.g. do not scp too early), and tested in integration tests
    update_existing: UpdateExisting = UpdateExisting.IF_EXISTS
    """Behavior if a resource with the same name already exists on the workunit."""

    protocol: Literal["scp"] = "scp"
    """Transfer protocol used to copy the file to storage; currently only ``"scp"`` is supported."""


class SaveDatasetSpec(BaseModel):
    """Uploads a local delimited file as the workunit's output dataset."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_dataset"] = "bfabric_dataset"

    local_path: Path
    """Path to the local delimited file to upload as the dataset."""

    separator: str
    """Field separator of the local file (e.g. a comma or a tab character)."""

    name: str | None = None
    """Name for the dataset in B-Fabric; ``None`` uses the local file's stem."""

    has_header: bool = True
    """Whether the local file's first row contains column names."""

    invalid_characters: str = ""
    """Characters that must not appear in any cell; upload fails if any occur (empty string disables the check)."""

    update_existing: UpdateExisting = UpdateExisting.IF_EXISTS
    """Behavior if the workunit already has an output dataset with the same name."""


class SaveLinkSpec(BaseModel):
    """Saves a link to the workunit, or, if desired to an arbitrary entity of type entity_type with id entity_id."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_link"] = "bfabric_link"
    name: str
    """The name of the link."""
    url: str
    """The URL of the link."""
    entity_type: str = "Workunit"
    """The type of the entity that will be linked."""
    entity_id: int | None = None
    """The ID of the entity that will be linked."""
    update_existing: UpdateExisting = UpdateExisting.IF_EXISTS
    """Behavior, if a link with the same name already exists."""

    @model_validator(mode="after")
    def require_entity_id_if_not_workunit(self) -> SaveLinkSpec:
        if self.entity_type != "Workunit" and self.entity_id is None:
            raise ValueError("entity_id must be provided if entity_type is not 'Workunit'")
        return self


SpecType = Annotated[CopyResourceSpec | SaveDatasetSpec | SaveLinkSpec, Field(discriminator="type")]


class OutputsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outputs: list[SpecType]

    @classmethod
    def read_yaml(cls, path: Path) -> list[SpecType]:
        model = cls.model_validate(yaml.safe_load(path.read_text()))
        return model.outputs

    @classmethod
    def write_yaml(cls, specs: list[SpecType], path: Path) -> None:
        model = cls.model_validate(dict(outputs=specs))
        path.write_text(yaml.dump(model.model_dump(mode="json")))

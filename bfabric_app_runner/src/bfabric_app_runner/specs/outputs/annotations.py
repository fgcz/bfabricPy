from __future__ import annotations

import typing
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel, model_validator


class IncludeDatasetRef(BaseModel):
    Formats: ClassVar = Literal["csv", "tsv", "parquet"]

    local_path: Path
    format: Formats | None = None

    def get_format(self) -> Formats:
        """Returns the format inferring the type from the filename if not specified explicitly."""
        if self.format is not None:
            return self.format
        return self.local_path.suffix.removeprefix(".")

    @model_validator(mode="after")
    def _check_format_or_correct_suffix(self) -> IncludeDatasetRef:
        allowed_formats = typing.get_args(self.Formats)
        if self.format is None and self.local_path.suffix.removeprefix(".") not in allowed_formats:
            msg = f"When format is not specified, the file extension must be one of {allowed_formats}"
            raise ValueError(msg)
        return self


class IncludeResourceRef(BaseModel):
    store_entry_path: Path
    anchor: str = ""
    metadata: dict[str, str] = {}


class BfabricOutputDataset(BaseModel):
    # Single discriminator value for now; when a second annotation type lands, add a default and migrate consumers.
    type: Literal["bfabric_output_dataset"]
    name: str | None = None
    include_tables: list[IncludeDatasetRef] = []
    include_resources: list[IncludeResourceRef] = []


AnnotationType = BfabricOutputDataset

from __future__ import annotations

import typing
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel, model_validator

from bfabric_app_runner.specs.outputs_spec import UpdateExisting


class IncludeDatasetRef(BaseModel):
    Formats: ClassVar = Literal["csv", "tsv", "parquet"]

    local_path: Path
    format: Formats | None = None

    # TODO decide if this is the correct place or it should be a level higher
    update_existing: UpdateExisting = UpdateExisting.IF_EXISTS

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
    # TODO None vs empty string
    anchor: str | None = None
    metadata: dict[str, str] = {}


class BfabricOutputDataset(BaseModel):
    # TODO since there is only one output annotation, we cannot set the default value yet, because
    #      adding more types later would be a breaking change otherwise.
    # type: Literal["bfabric_output_dataset"] = "bfabric_output_dataset"
    type: Literal["bfabric_output_dataset"]
    include_tables: list[IncludeDatasetRef]
    include_resources: list[IncludeResourceRef]


AnnotationType = BfabricOutputDataset

from __future__ import annotations
from typing import Literal

from pydantic import BaseModel, ConfigDict

from bfabric_app_runner.specs.common_types import RelativeFilePath


class BfabricOrderFastaSpec(BaseModel):
    """Writes the FASTA sequence attached to a B-Fabric order to a file."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_order_fasta"] = "bfabric_order_fasta"
    """Discriminator marking this input as an order FASTA."""

    id: int
    """ID of the entity to resolve the order from (see ``entity``)."""

    entity: Literal["workunit", "order"]
    """Whether ``id`` refers to an order directly, or to a workunit whose order is used."""

    filename: RelativeFilePath
    """Target filename (relative to the chunk directory) to write the FASTA sequence to."""

    required: bool = False
    """If True, a missing order or FASTA sequence raises an error; otherwise an empty file is written."""

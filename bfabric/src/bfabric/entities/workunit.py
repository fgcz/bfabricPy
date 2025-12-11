from __future__ import annotations

import warnings
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_many import HasMany
from bfabric.entities.core.has_one import HasOne
from bfabric.entities.core.mixins.user_created_mixin import UserCreatedMixin
from bfabric.utils.path_safe_name import path_safe_name

if TYPE_CHECKING:
    from bfabric.entities import Application, Dataset, ExternalJob, Order, Parameter, Project, Resource


class Workunit(Entity, UserCreatedMixin):
    """Immutable representation of a single workunit in B-Fabric."""

    ENDPOINT = "workunit"

    application: HasOne[Application] = HasOne(bfabric_field="application")
    container: HasOne[Order | Project] = HasOne(bfabric_field="container")
    parameters: HasMany[Parameter] = HasMany(bfabric_field="parameter", optional=True)
    resources: HasMany[Resource] = HasMany(bfabric_field="resource", optional=True)
    input_resources: HasMany[Resource] = HasMany(bfabric_field="inputresource", optional=True)
    input_dataset: HasOne[Dataset] = HasOne(bfabric_field="inputdataset", optional=True)
    external_jobs: HasMany[ExternalJob] = HasMany(bfabric_field="externaljob", optional=True)

    @cached_property
    def application_parameters(self) -> dict[str, str]:
        """Dictionary of application context parameters."""
        return {p.key: p.value for p in self.parameters if p["context"] == "APPLICATION"}

    @cached_property
    def submitter_parameters(self) -> dict[str, str]:
        """Dictionary of submitter context parameters."""
        return {p.key: p.value for p in self.parameters if p["context"] == "SUBMITTER"}

    @cached_property
    def workunit_parameters(self) -> dict[str, str]:
        """Dictionary of workunit context parameters."""
        return {p.key: p.value for p in self.parameters if p["context"] == "WORKUNIT"}

    @cached_property
    def parameter_values(self) -> dict[str, str]:
        # Deprecated
        warnings.warn(
            "The parameter_values property is deprecated and will be removed in a future version. "
            "Use application_parameters or submitter_parameters instead.",
            DeprecationWarning,
        )
        return {p.key: p.value for p in self.parameters.list}

    @cached_property
    def store_output_folder(self) -> Path:
        """Relative path in the storage for the workunit output."""
        if self.application is None:
            raise ValueError("Cannot determine the storage path without an application.")
        if self.application.storage is None:
            raise ValueError("Cannot determine the storage path without an application storage configuration.")
        date = self.created_at
        return Path(
            f"{self.application.storage['projectfolderprefix']}{self.container.id}",
            "bfabric",
            self.application.technology_folder_name,
            path_safe_name(self.application["name"]),
            date.strftime("%Y/%Y-%m/%Y-%m-%d/"),
            f"workunit_{self.id}",
        )

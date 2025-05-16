from __future__ import annotations

import warnings
from functools import cached_property
from pathlib import Path
from typing import Any, TYPE_CHECKING

import dateutil.parser

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_container_mixin import HasContainerMixin
from bfabric.entities.core.has_many import HasMany
from bfabric.entities.core.has_one import HasOne
from bfabric.utils.path_safe_name import path_safe_name

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities.application import Application
    from bfabric.entities.dataset import Dataset
    from bfabric.entities.externaljob import ExternalJob
    from bfabric.entities.parameter import Parameter
    from bfabric.entities.resource import Resource


class Workunit(Entity, HasContainerMixin):
    """Immutable representation of a single workunit in B-Fabric.
    :param data_dict: The dictionary representation of the workunit.
    """

    ENDPOINT = "workunit"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None = None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    application: HasOne[Application] = HasOne(entity="Application", bfabric_field="application")
    parameters: HasMany[Parameter] = HasMany(entity="Parameter", bfabric_field="parameter", optional=True)
    resources: HasMany[Resource] = HasMany(entity="Resource", bfabric_field="resource", optional=True)
    input_resources: HasMany[Resource] = HasMany(entity="Resource", bfabric_field="inputresource", optional=True)
    input_dataset: HasOne[Dataset] = HasOne(entity="Dataset", bfabric_field="inputdataset", optional=True)
    external_jobs: HasMany[ExternalJob] = HasMany(entity="ExternalJob", bfabric_field="externaljob", optional=True)

    @cached_property
    def application_parameters(self) -> dict[str, str]:
        """Dictionary of application context parameters."""
        return {p.key: p.value for p in self.parameters if p["context"] == "APPLICATION"}

    @cached_property
    def submitter_parameters(self) -> dict[str, str]:
        """Dictionary of submitter context parameters."""
        return {p.key: p.value for p in self.parameters if p["context"] == "SUBMITTER"}

    @cached_property
    def parameter_values(self) -> dict[str, Any]:
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
        date = dateutil.parser.parse(self.data_dict["created"])
        return Path(
            f"{self.application.storage['projectfolderprefix']}{self.container.id}",
            "bfabric",
            self.application.technology_folder_name,
            path_safe_name(self.application["name"]),
            date.strftime("%Y/%Y-%m/%Y-%m-%d/"),
            f"workunit_{self.id}",
        )

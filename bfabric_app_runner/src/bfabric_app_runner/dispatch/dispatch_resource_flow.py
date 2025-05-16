from pathlib import Path
from typing import Protocol, Any

import cyclopts
import pandera.polars as pa
import polars as pl
import yaml
from pandera import Field
from pandera.typing.polars import DataFrame

from bfabric import Bfabric
from bfabric.entities import Resource
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric.utils.cli_integration import use_client


class InputTable(pa.DataFrameModel):
    resource_id: int
    filename: str
    relativepath: str


class OutputTable(pa.DataFrameModel):
    class Config:
        coerce = True
        add_missing_columns = True

    resource_id: int
    filename: str = Field(nullable=True)
    task: str = Field(default=pl.lit("work"), str_matches=r"^\w+$")


class DispatchResource(Protocol):
    """A callable that dispatches resources for processing.

    It receives a table of all available resources and returns a table of
    resources to be processed by the workunit.

    If you check the difference between `InputTable` and `OutputTable`, you can see that `OutputTable` has an additional
    field `task` which is set to the string "work". If your workunit entails separate tasks to be computed, you can
    assign different values to the `task` field to differentiate between them.
    """

    def __call__(
        self, resources_df: DataFrame[InputTable], workunit_definition: WorkunitDefinition
    ) -> DataFrame[OutputTable] | tuple[DataFrame[OutputTable], list[dict[str, Any]]]:
        """Return a table of resources to be processed by the workunit.

        :param resources_df: Input DataFrame to be processed, of InputTable schema
        :param workunit_definition: The workunit definition, if you need additional information
        :return:
          - Output DataFrame to be processed, of OutputTable schema
          - Optional: a list of additional input specs to add to the inputs.yml file (if multiple tasks are generated,
            this will be added to each task's inputs.yml file)
        """
        ...


class ResourceDispatcher:
    def dispatch(
        self,
        workunit_definition: WorkunitDefinition,
        work_dir: Path,
        resource_strategy: DispatchResource,
        *,
        client: Bfabric,
    ) -> None:
        """Dispatches a resource flow workunit with the specified resource strategy.

        :param workunit_definition: The workunit definition to dispatch.
        :param work_dir: The workunit working directory.
        :param resource_strategy: The resource dispatch strategy.
        :param client: The B-Fabric client to use.
        """
        extra_inputs, requested_table, tasks = self._determine_requested_inputs(
            client=client, resource_strategy=resource_strategy, workunit_definition=workunit_definition
        )
        for task in tasks:
            self._create_task_dir(
                extra_inputs=extra_inputs, requested_table=requested_table, task=task, work_dir=work_dir
            )

        # Generate the `chunks.yml` file
        with (work_dir / "chunks.yml").open("w") as f:
            yaml.safe_dump({"chunks": tasks}, f)

    @staticmethod
    def _build_input_resources_df(resource_ids: list[int], client: Bfabric) -> DataFrame[InputTable]:
        """Creates the InputTable DataFrame from the list of resource IDs."""
        resources = Resource.find_all(resource_ids, client=client).values()
        if not resources:
            raise ValueError("No resources to dispatch")
        attributes = [
            {
                "resource_id": resource["id"],
                "filename": Path(resource["relativepath"]).name,
                "relativepath": resource["relativepath"],
            }
            for resource in resources
        ]
        df = pl.DataFrame(attributes)
        return InputTable.validate(df)

    @staticmethod
    def _build_inputs_spec(inputs: DataFrame[OutputTable]) -> dict[str, list[dict]]:
        """Builds input specs from the OutputTable DataFrame."""
        specs = []
        for row in inputs.iter_rows(named=True):
            specs.append({"type": "bfabric_resource", "id": row["resource_id"], "filename": row["filename"]})
        return {"inputs": specs}

    @staticmethod
    def _evaluate_strategy(
        input_resources_df: DataFrame[InputTable],
        workunit_definition: WorkunitDefinition,
        resource_strategy: DispatchResource,
    ) -> tuple[DataFrame[OutputTable], list[dict[str, Any]]]:
        result = resource_strategy(input_resources_df, workunit_definition)
        if isinstance(result, tuple):
            return OutputTable.validate(result[0]), result[1]
        return OutputTable.validate(result), []

    def _determine_requested_inputs(
        self, client: Bfabric, resource_strategy: DispatchResource, workunit_definition: WorkunitDefinition
    ) -> tuple[list[dict[str, Any]], DataFrame[OutputTable], list[str]]:
        input_resources_df = self._build_input_resources_df(
            resource_ids=workunit_definition.execution.resources, client=client
        )
        requested_table, extra_inputs = self._evaluate_strategy(
            input_resources_df=input_resources_df,
            workunit_definition=workunit_definition,
            resource_strategy=resource_strategy,
        )
        tasks = sorted(requested_table["task"].unique())
        return extra_inputs, requested_table, tasks

    def _create_task_dir(
        self, extra_inputs: list[dict[str, Any]], requested_table: DataFrame[OutputTable], task: str, work_dir: Path
    ) -> None:
        """Creates a task directory with the specified inputs."""
        task_dir = work_dir / task
        task_dir.mkdir(exist_ok=True, parents=True)

        # Generate the task `inputs.yml` file
        task_inputs = requested_table.filter(pl.col("task") == pl.lit(task))
        inputs_spec = self._build_inputs_spec(task_inputs)
        inputs_spec["inputs"].extend(extra_inputs)
        with (task_dir / "inputs.yml").open("w") as f:
            yaml.safe_dump(inputs_spec, f)


class ResourceDispatcherCLI:
    """A CLI interface for dispatching resources to workunits."""

    def __init__(self, resource_strategy: DispatchResource) -> None:
        self._resource_strategy = resource_strategy
        self._app = cyclopts.App()
        self._app.default(self.main)

    def run(self) -> None:
        """Runs the CLI application."""
        self._app()

    @use_client
    def main(self, workunit_ref: Path | int, out_dir: Path, *, client: Bfabric) -> None:
        """Dispatches resources to a workunit."""
        workunit_definition = WorkunitDefinition.from_ref(workunit_ref, client=client)
        dispatcher = ResourceDispatcher()
        dispatcher.dispatch(
            workunit_definition=workunit_definition,
            work_dir=out_dir,
            resource_strategy=self._resource_strategy,
            client=client,
        )

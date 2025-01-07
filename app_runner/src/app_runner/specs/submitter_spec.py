from typing import Literal, Any

from pydantic import BaseModel


class SubmitterSlurmSpec(BaseModel):
    type: Literal["slurm22"] = "slurm22"
    n_nodes: int | tuple[int, int] = 1
    n_tasks: int = 1
    n_cpus: int
    n_cpus_scope: Literal["task", "gpu"] = "task"
    partition: str
    memory: str
    memory_scope: Literal["node", "cpu", "gpu"] = "node"
    nodelist: str | None = None
    time: str | None = None
    disk: int | None = None
    log_stdout: str | None = None
    log_stderr: str | None = None
    custom_args: dict[str, str | None] = {}

    def get_slurm_parameters(self) -> dict[str, str | None]:
        params = {}
        if isinstance(self.n_nodes, int):
            params["nodes"] = str(self.n_nodes)
        else:
            params["nodes"] = f"{self.n_nodes[0]}-{self.n_nodes[1]}"

        if self.n_cpus_scope == "task":
            params["cpus-per-task"] = str(self.n_cpus)
        elif self.n_cpus_scope == "gpu":
            params["cpus-per-gpu"] = str(self.n_cpus)

        if self.memory_scope == "node":
            params["mem"] = self.memory
        elif self.memory_scope == "cpu":
            params["mem-per-cpu"] = self.memory
        elif self.memory_scope == "gpu":
            params["mem-per-gpu"] = self.memory

        if self.nodelist:
            params["nodelist"] = self.nodelist
        if self.time:
            params["time"] = self.time
        if self.disk:
            params["disk"] = str(self.disk)
        if self.log_stdout:
            params["output"] = self.log_stdout
        if self.log_stderr:
            params["error"] = self.log_stderr
        return params

    def to_slurm_cli_arguments(self) -> list[str]:
        args = []
        params = self.get_slurm_parameters()
        for name, value in params.items():
            if value is None:
                args.append(f"--{name}")
            else:
                args.append(f"--{name}={value}")
        # args.extend(self.custom_args)
        return args


class SubmitterRef(BaseModel):
    name: str
    config: dict[str, Any] = {}

    def resolve(self, specs: dict[str, SubmitterSlurmSpec]) -> SubmitterSlurmSpec:
        base_spec = specs[self.name]
        base = base_spec.model_dump(mode="json")
        base.update(self.config)
        return type(base_spec).model_validate(base)


class SubmittersSpec(BaseModel):
    submitters: dict[str, SubmitterSlurmSpec]

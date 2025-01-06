from typing import Literal, Any

from pydantic import BaseModel


class SubmitterSlurmSpec(BaseModel):
    type: Literal["slurm22"] = "slurm22"
    n_nodes: int | tuple[int, int] = 1
    n_tasks: int = 1
    n_cpus_per_task: int
    partition: str
    memory_per_cpu: str
    nodelist: str | None = None
    time: str | None = None
    disk: int | None = None
    log_stdout: str | None = None
    log_stderr: str | None = None
    custom_args: list[str] = []

    def to_slurm_args(self) -> list[str]:
        args = []
        if isinstance(self.n_nodes, int):
            args.append(f"--nodes={self.n_nodes}")
        else:
            args.append(f"--nodes={self.n_nodes[0]}-{self.n_nodes[1]}")
        args.append(f"--partition={self.partition}")
        args.append(f"--cpus-per-task={self.n_cpus_per_task}")
        args.append(f"--mem={self.memory_per_cpu}")
        if self.nodelist:
            args.append(f"--nodelist={self.nodelist}")
        if self.time:
            args.append(f"--time={self.time}")
        if self.disk:
            args.append(f"--disk={self.disk}")
        if self.log_stdout:
            args.append(f"--output={self.log_stdout}")
        if self.log_stderr:
            args.append(f"--error={self.log_stderr}")
        # TODO there should be at least some checks to avoid collision (maybe as a validator)
        args.extend(self.custom_args)
        return args


class SubmitterRef(BaseModel):
    name: str
    config: dict[str, Any] = {}

    def resolve(self, specs: dict[str, SubmitterSlurmSpec]) -> SubmitterSlurmSpec:
        base_spec = specs[self.name]
        base = base_spec.model_dump(mode="json")
        base.update(self.config)
        return type(base_spec).model_validate(base)

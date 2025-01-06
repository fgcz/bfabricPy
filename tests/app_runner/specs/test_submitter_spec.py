import pytest

from app_runner.specs.submitter_spec import SubmitterSlurmSpec, SubmitterRef


@pytest.fixture
def spec_base() -> SubmitterSlurmSpec:
    config_data = {
        "partition": "prx",
        "nodelist": "fgcz-r-033",
        "n_nodes": 1,
        "n_tasks": 1,
        "n_cpus_per_task": 1,
        "memory": "1G",
    }
    return SubmitterSlurmSpec.model_validate(config_data)


@pytest.fixture
def specs_base(spec_base) -> dict[str, SubmitterSlurmSpec]:
    return {"slurm": spec_base}


def test_resolve(specs_base):
    ref = SubmitterRef(name="slurm", config={"n_nodes": 2})
    resolved = ref.resolve(specs_base)
    assert resolved.memory == "1G"
    assert resolved.n_nodes == 2

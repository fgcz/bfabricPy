import pytest

from app_runner.specs.submitter_spec import SubmitterSlurmSpec, SubmitterRef


@pytest.fixture
def spec_base_data() -> dict[str, str | int]:
    return {
        "partition": "prx",
        "nodelist": "fgcz-r-033",
        "n_nodes": 1,
        "n_tasks": 1,
        "n_cpus": 1,
        "memory": "1G",
        "custom_args": {},
    }


@pytest.fixture
def spec_base(spec_base_data) -> SubmitterSlurmSpec:
    return SubmitterSlurmSpec.model_validate(spec_base_data)


@pytest.fixture
def specs_base(spec_base) -> dict[str, SubmitterSlurmSpec]:
    return {"slurm": spec_base}


def test_ban_extra_arg_in_main_spec(spec_base_data):
    spec_base_data["custom_args"]["cpus-per-task"] = 5
    with pytest.raises(ValueError):
        SubmitterSlurmSpec.model_validate(spec_base_data)


def test_resolve(specs_base):
    ref = SubmitterRef(name="slurm", config={"n_nodes": 2})
    resolved = ref.resolve(specs_base)
    assert resolved.memory == "1G"
    assert resolved.n_nodes == 2

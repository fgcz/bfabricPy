import pytest
from bfabric.entities.dataset import Dataset
from bfabric.entities.externaljob import ExternalJob
from bfabric.entities.core.import_entity import import_entity


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Dataset", Dataset),
        ("dataset", Dataset),
        ("ExternalJob", ExternalJob),
        ("Externaljob", ExternalJob),
        ("externaljob", ExternalJob),
    ],
)
def test_import_entity(name, expected):
    entity = import_entity(name)
    assert entity is expected

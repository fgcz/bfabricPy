import pytest
from bfabric.entities.dataset import Dataset
from bfabric.entities.externaljob import ExternalJob
from bfabric.entities.core.import_entity import entity_type_of, import_entity

from bfabric.entities.core.entity import Entity


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Dataset", Dataset),
        ("dataset", Dataset),
        ("ExternalJob", ExternalJob),
        ("Externaljob", ExternalJob),
        ("externaljob", ExternalJob),
        ("neverexisted", Entity),
        (" cant exist", Entity),
    ],
)
def test_import_entity(name, expected):
    entity = import_entity(name)
    assert entity is expected


@pytest.mark.parametrize("entity_class", [Dataset, ExternalJob])
def test_entity_type_of_is_lowercase_class_name(entity_class):
    assert entity_type_of(entity_class) == entity_class.__name__.lower()


@pytest.mark.parametrize("entity_class", [Dataset, ExternalJob])
def test_entity_type_of_round_trips_with_import_entity(entity_class):
    # entity_type_of is the class→string inverse of import_entity's string→class mapping
    assert import_entity(entity_type_of(entity_class)) is entity_class

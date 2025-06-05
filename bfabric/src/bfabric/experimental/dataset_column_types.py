import importlib.resources
import yaml
from pydantic import BaseModel


class DatasetColumnTypes(BaseModel):
    entities: set[str]
    """List of dataset column types for referencing entities, e.g. Resource, Dataset, Sample."""


class DatasetColumnTypesFile(BaseModel):
    dataset_column_types: DatasetColumnTypes


def get_dataset_column_types() -> DatasetColumnTypes:
    """Parses the default dataset_column_types.yml file from the package."""
    with importlib.resources.open_text("bfabric.experimental", "dataset_column_types.yml") as f:
        return DatasetColumnTypesFile.model_validate(yaml.safe_load(f)).dataset_column_types

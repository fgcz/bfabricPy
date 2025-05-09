# TODO this should be moved later
from collections.abc import Generator
from pathlib import Path
from typing import TypeVar

import pytest
import yaml
from _pytest.fixtures import FixtureRequest
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def yaml_fixture(model_class: type[T], fixture_name: str) -> Generator[T, None, None]:
    """Create a pytest fixture that loads a YAML file into a Pydantic model.

    :param model_class: The Pydantic model class to parse the YAML into
    :type model_class: Type[T]
    :param fixture_name: Name of the YAML file (without extension)
    :type fixture_name: str
    :return: A pytest fixture function that returns the parsed model
    :rtype: pytest.fixture

    :Example:

    .. code-block:: python

        class User(BaseModel):
            name: str
            email: str


        # Will load from tests/fixtures/test_user.yml
        user = yaml_fixture(User, "test_user")
    """

    @pytest.fixture
    def _fixture(request: FixtureRequest) -> T:
        fixtures_dir = Path(request.module.__file__).parent / "fixtures"
        fixture_path = fixtures_dir / f"{fixture_name}.yml"

        with fixture_path.open() as f:
            data = yaml.safe_load(f)
        return model_class.model_validate(data)

    return _fixture

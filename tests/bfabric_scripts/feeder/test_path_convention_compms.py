from pathlib import Path

import pytest

from bfabric_scripts.feeder.path_convention_compms import PathConventionCompMS
from bfabric.entities import Storage


@pytest.fixture
def mock_storage(mocker):
    data_dict = {"projectfolderprefix": "x", "basepath": "/base/path"}
    return Storage(data_dict, client=None, bfabric_instance="https://example.com/bfabric/")


@pytest.fixture
def path_convention(mock_storage):
    return PathConventionCompMS(storage=mock_storage)


def test_parse_absolute_path(mocker, path_convention):
    parse_relative = mocker.patch.object(PathConventionCompMS, "parse_relative_path")
    result = path_convention.parse_absolute_path(
        absolute_path=Path("/base/path/x3000/Proteomics/LUMOS_1/tester_20250525_test/20250525_014_autoQC01_S1234.raw")
    )
    assert result == parse_relative.return_value
    parse_relative.assert_called_once_with(
        relative_path=Path("x3000/Proteomics/LUMOS_1/tester_20250525_test/20250525_014_autoQC01_S1234.raw")
    )


def test_parse_relative_path_without_sample_id(path_convention) -> None:
    path = Path("x3000/Proteomics/LUMOS_1/tester_20250525_test/20250525_014_autoQC01_S1234.raw")
    parsed = path_convention.parse_relative_path(relative_path=path)
    assert parsed.absolute_path == Path("/base/path") / path
    assert parsed.relative_path == path
    assert parsed.container_id == 3000
    assert parsed.technology_name == "Proteomics"
    assert parsed.application_name == "LUMOS_1"
    assert parsed.sample_id is None


# TODO check if this should be added later
# def test_parse_relative_path_with_sample_id(mock_storage) -> None:
#    path = Path("x3000/Proteomics/FGCZ_LUMOS_1/tester_20250525_test/20250525_014_S1234_autoQC01.raw")
#    parsed = PathConventionCompMS(storage=mock_storage).parse_relative_path(relative_path=path)
#    assert parsed.relative_path == path
#    assert parsed.container_id == 3000
#    assert parsed.technology_name == "Proteomics"
#    assert parsed.application_name == "FGCZ_LUMOS_1"
#    assert parsed.sample_id == 1234

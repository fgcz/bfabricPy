from pathlib import Path
import pytest
from bfabric_app_runner.specs.outputs.annotations import IncludeDatasetRef


class TestIncludeDatasetRef:
    @pytest.mark.parametrize("format", ["csv", "tsv", "parquet"])
    def test_get_format_when_unspecified(self, format):
        ref = IncludeDatasetRef(local_path=Path(f"dummy.{format}"), format=None)
        assert ref.format is None
        assert ref.get_format() == format

    @pytest.mark.parametrize("format", ["csv", "tsv", "parquet"])
    def test_get_format_when_specified(self, format):
        ref = IncludeDatasetRef(local_path=Path("dummy.png"), format=format)
        assert ref.format == format
        assert ref.get_format() == format

    def test_validate_invalid_suffix_when_format_unspecified(self):
        with pytest.raises(ValueError) as err:
            _ = IncludeDatasetRef(local_path=Path("dummy.png"), format=None)
        assert (
            err.value.errors()[0]["msg"]
            == "Value error, When format is not specified, the file extension must be one of ('csv', 'tsv', 'parquet')"
        )

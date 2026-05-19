from pathlib import Path

import pytest
from bfabric import Bfabric
from bfabric.entities import Dataset
from bfabric_scripts.cli.dataset.download import (
    Params,
    OutputFormat,
    _infer_format_from_path,
    cmd_dataset_download,
)
from pytest_mock import MockFixture


@pytest.fixture
def mock_client(mocker):
    client = mocker.Mock(spec=Bfabric)
    client.config.base_url = "http://test-bfabric.com"
    return client


@pytest.fixture
def mock_dataset(mocker):
    dataset = mocker.Mock(spec=Dataset)
    dataset.to_polars.return_value = mocker.MagicMock()
    dataset.write_csv.return_value = None
    return dataset


class TestInferFormatFromPath:
    def test_infer_csv_format(self):
        path = Path("output.csv")
        assert _infer_format_from_path(path) == OutputFormat.CSV

    def test_infer_tsv_format(self):
        path = Path("output.tsv")
        assert _infer_format_from_path(path) == OutputFormat.TSV

    def test_infer_parquet_format(self):
        path = Path("output.parquet")
        assert _infer_format_from_path(path) == OutputFormat.PARQUET

    def test_infer_excel_format(self):
        path = Path("output.xlsx")
        assert _infer_format_from_path(path) == OutputFormat.EXCEL

    def test_infer_format_case_insensitive(self):
        path = Path("output.CSV")
        assert _infer_format_from_path(path) == OutputFormat.CSV

    def test_infer_format_unknown_extension(self):
        path = Path("output.txt")
        with pytest.raises(ValueError, match="Cannot infer format from file extension"):
            _infer_format_from_path(path)

    def test_infer_format_no_extension(self):
        path = Path("output")
        with pytest.raises(ValueError, match="Cannot infer format from file extension"):
            _infer_format_from_path(path)


class TestCmdDatasetDownload:
    def test_download_csv_format(self, mocker, mock_client, mock_dataset, tmp_path):
        mocker.patch.object(Dataset, "find", return_value=mock_dataset)
        output_file = tmp_path / "output.csv"
        output_file.touch()
        params = Params(dataset_id=123, file=output_file, format=OutputFormat.CSV)

        cmd_dataset_download(params, client=mock_client)

        mock_dataset.write_csv.assert_called_once()
        args, kwargs = mock_dataset.write_csv.call_args
        assert kwargs["separator"] == ","

    def test_download_tsv_format(self, mocker, mock_client, mock_dataset, tmp_path):
        mocker.patch.object(Dataset, "find", return_value=mock_dataset)
        output_file = tmp_path / "output.tsv"
        output_file.touch()
        params = Params(dataset_id=123, file=output_file, format=OutputFormat.TSV)

        cmd_dataset_download(params, client=mock_client)

        mock_dataset.write_csv.assert_called_once()
        args, kwargs = mock_dataset.write_csv.call_args
        assert kwargs["separator"] == "\t"

    def test_download_parquet_format(self, mocker, mock_client, mock_dataset, tmp_path):
        mocker.patch.object(Dataset, "find", return_value=mock_dataset)
        output_file = tmp_path / "output.parquet"
        output_file.touch()
        params = Params(dataset_id=123, file=output_file, format=OutputFormat.PARQUET)

        cmd_dataset_download(params, client=mock_client)

        mock_dataset.to_polars.return_value.write_parquet.assert_called_once()

    def test_download_excel_format_with_fastexcel(self, mocker, mock_client, mock_dataset, tmp_path):
        mocker.patch.object(Dataset, "find", return_value=mock_dataset)
        mocker.patch("bfabric_scripts.cli.dataset.download.is_excel_available", return_value=True)
        output_file = tmp_path / "output.xlsx"
        output_file.touch()
        params = Params(dataset_id=123, file=output_file, format=OutputFormat.EXCEL)

        cmd_dataset_download(params, client=mock_client)

        mock_dataset.to_polars.return_value.write_excel.assert_called_once()

    def test_download_excel_format_without_fastexcel(self, mocker, mock_client, mock_dataset):
        mocker.patch.object(Dataset, "find", return_value=mock_dataset)
        mocker.patch("bfabric_scripts.cli.dataset.download.is_excel_available", return_value=False)
        params = Params(dataset_id=123, file=Path("output.xlsx"), format=OutputFormat.EXCEL)

        with pytest.raises(RuntimeError, match="Excel format requires the 'excel' optional dependency"):
            cmd_dataset_download(params, client=mock_client)

    def test_download_auto_format_csv(self, mocker, mock_client, mock_dataset, tmp_path):
        mocker.patch.object(Dataset, "find", return_value=mock_dataset)
        output_file = tmp_path / "output.csv"
        output_file.touch()
        params = Params(dataset_id=123, file=output_file, format=OutputFormat.AUTO)

        cmd_dataset_download(params, client=mock_client)

        mock_dataset.write_csv.assert_called_once()

    def test_download_auto_format_excel(self, mocker, mock_client, mock_dataset, tmp_path):
        mocker.patch.object(Dataset, "find", return_value=mock_dataset)
        mocker.patch("bfabric_scripts.cli.dataset.download.is_excel_available", return_value=True)
        output_file = tmp_path / "output.xlsx"
        output_file.touch()
        params = Params(dataset_id=123, file=output_file, format=OutputFormat.AUTO)

        cmd_dataset_download(params, client=mock_client)

        mock_dataset.to_polars.return_value.write_excel.assert_called_once()

    def test_download_auto_format_unknown_extension(self, mocker, mock_client, mock_dataset):
        mocker.patch.object(Dataset, "find", return_value=mock_dataset)
        params = Params(dataset_id=123, file=Path("output.txt"), format=OutputFormat.AUTO)

        with pytest.raises(ValueError, match="Cannot infer format from file extension"):
            cmd_dataset_download(params, client=mock_client)

    def test_download_dataset_not_found(self, mocker, mock_client):
        mocker.patch.object(Dataset, "find", return_value=None)
        params = Params(dataset_id=999, file=Path("output.csv"), format=OutputFormat.CSV)

        with pytest.raises(ValueError, match="Dataset with id 999 not found"):
            cmd_dataset_download(params, client=mock_client)

    def test_download_creates_directory(self, mocker, mock_client, mock_dataset, tmp_path):
        mocker.patch.object(Dataset, "find", return_value=mock_dataset)
        output_dir = tmp_path / "subdir" / "nested"
        output_file = output_dir / "output.csv"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.touch()
        params = Params(dataset_id=123, file=output_file, format=OutputFormat.CSV)

        cmd_dataset_download(params, client=mock_client)

        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_download_explicit_format_overrides_extension(self, mocker, mock_client, mock_dataset, tmp_path):
        mocker.patch.object(Dataset, "find", return_value=mock_dataset)
        output_file = tmp_path / "output.csv"
        output_file.touch()
        params = Params(dataset_id=123, file=output_file, format=OutputFormat.TSV)

        cmd_dataset_download(params, client=mock_client)

        args, kwargs = mock_dataset.write_csv.call_args
        assert kwargs["separator"] == "\t"


if __name__ == "__main__":
    pytest.main(["-vv", __file__])

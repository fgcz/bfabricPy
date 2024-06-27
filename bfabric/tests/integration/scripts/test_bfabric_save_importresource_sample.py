from pathlib import Path
from unittest.mock import ANY

import pytest
from pytest_mock import MockerFixture

from bfabric.scripts.bfabric_save_importresource_sample import (
    get_sample_id_from_path,
    get_bfabric_application_and_project_id,
    create_importresource_dict,
    get_file_attributes,
)


def test_get_sample_id_from_path_when_match():
    example_path = "p123/Proteomics/A_1/abc_002_S123456_hello.zip"
    assert get_sample_id_from_path(example_path) == 123456


def test_get_sample_id_from_path_when_none():
    example_path = "p123/Proteomics/A_1/abc_002_S123456_hello.txt"
    assert get_sample_id_from_path(example_path) is None


def test_get_bfabric_application_and_project_id_when_match():
    bfabric_application_ids = {"bestapp": 500}
    example_path = "p123/Proteomics/bestapp/abc_002_S123456_hello.zip"
    assert get_bfabric_application_and_project_id(bfabric_application_ids, example_path) == (500, 123)


def test_get_bfabric_application_and_project_id_when_no_match():
    bfabric_application_ids = {"bestapp": 500}
    example_path = "p123/Proteomics/otherapp/abc_002_S123456_hello.zip"
    with pytest.raises(RuntimeError):
        get_bfabric_application_and_project_id(bfabric_application_ids, example_path)


@pytest.mark.parametrize("sample_id", [123456, None])
def test_create_importresource_dict(mocker: MockerFixture, sample_id: int | None):
    file_unix_timestamp = 123000
    if sample_id:
        file_path = f"p123/Proteomics/A_1/abc_002_S{sample_id}_hello.zip"
    else:
        file_path = "p123/Proteomics/A_1/abc_002_123456_hello.txt"
    mock_config = mocker.MagicMock(name="config", application_ids={"bestapp": 500})
    mock_get_application_and_project_id = mocker.patch(
        "bfabric.scripts.bfabric_save_importresource_sample.get_bfabric_application_and_project_id"
    )
    mock_get_application_and_project_id.return_value = (500, 123)

    obj = create_importresource_dict(
        config=mock_config,
        file_path=file_path,
        file_size=123,
        file_unix_timestamp=file_unix_timestamp,
        md5_checksum="123",
    )

    expected = {
        "applicationid": 500,
        "filechecksum": "123",
        "containerid": 123,
        "filedate": "1970-01-02 10:10:00",
        "relativepath": file_path,
        "name": Path(file_path).name,
        "size": 123,
        "storageid": 2,
    }
    if sample_id is not None:
        expected["sampleid"] = sample_id

    assert obj == expected


def test_get_file_attributes_when_parsed() -> None:
    attributes = "abcdef123456;1000;50000;my/file.txt"
    assert get_file_attributes(attributes) == ("abcdef123456", 1000, 50000, "my/file.txt")


def test_get_file_attributes_when_filename(tmp_path: Path) -> None:
    tmp_file = tmp_path / "my_file.txt"
    tmp_file.write_text("hello")
    expected_hash = "5d41402abc4b2a76b9719d911017c592"
    assert get_file_attributes(str(tmp_file)) == (expected_hash, ANY, 5, str(tmp_file))


def test_get_file_attributes_when_invalid() -> None:
    attributes = "abcdef123;1000;50000;my;file.txt"
    with pytest.raises(ValueError):
        get_file_attributes(attributes)


if __name__ == "__main__":
    pytest.main()

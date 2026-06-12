"""TDD tests for bfabric_upload_workunit_folder.

Run with:
    pytest tests/bfabric_scripts/test_upload_workunit_folder.py
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest


class TestCollectFiles:
    """Unit tests for _collect_files helper."""

    def test_rejects_symlink_file(self, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import _collect_files

        real = tmp_path / "real.txt"
        real.write_text("hello")
        (tmp_path / "link.txt").symlink_to(real)
        with pytest.raises(ValueError, match="Symlinks are not allowed"):
            _collect_files(tmp_path)

    def test_rejects_symlink_dir(self, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import _collect_files

        real_dir = tmp_path / "realdir"
        real_dir.mkdir()
        (real_dir / "file.txt").write_text("x")
        (tmp_path / "linkdir").symlink_to(real_dir)
        with pytest.raises(ValueError, match="Symlinks are not allowed"):
            _collect_files(tmp_path)

    def test_skips_hidden_file(self, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import _collect_files

        (tmp_path / "visible.txt").write_text("a")
        (tmp_path / ".hidden").write_text("b")
        files = _collect_files(tmp_path)
        assert [f.name for f in files] == ["visible.txt"]

    def test_skips_files_in_hidden_dir(self, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import _collect_files

        (tmp_path / ".hidden_dir").mkdir()
        (tmp_path / ".hidden_dir" / "file.txt").write_text("x")
        (tmp_path / "visible.txt").write_text("y")
        files = _collect_files(tmp_path)
        assert [f.name for f in files] == ["visible.txt"]

    def test_collects_nested_files(self, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import _collect_files

        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        files = _collect_files(tmp_path)
        assert {f.relative_to(tmp_path) for f in files} == {Path("sub/a.txt"), Path("b.txt")}

    def test_returns_empty_for_empty_folder(self, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import _collect_files

        assert _collect_files(tmp_path) == []


class TestValidateDeliveryFolder:
    """Unit tests for _validate_delivery_folder helper."""

    def test_rejects_nonexistent_path(self, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import _validate_delivery_folder

        with pytest.raises(ValueError, match="does not exist"):
            _validate_delivery_folder(tmp_path / "nope")

    def test_rejects_file_path(self, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import _validate_delivery_folder

        f = tmp_path / "file.txt"
        f.write_text("x")
        with pytest.raises(ValueError, match="Not a directory"):
            _validate_delivery_folder(f)

    def test_rejects_empty_folder(self, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import _validate_delivery_folder

        with pytest.raises(ValueError, match="empty"):
            _validate_delivery_folder(tmp_path)

    def test_returns_file_list_for_valid_folder(self, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import _validate_delivery_folder

        (tmp_path / "result.txt").write_text("data")
        files = _validate_delivery_folder(tmp_path)
        assert len(files) == 1
        assert files[0].name == "result.txt"


class TestFindExistingResourceId:
    """Unit tests for _find_existing_resource_id helper."""

    def test_returns_none_when_not_found(self) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import _find_existing_resource_id

        client = MagicMock()
        client.reader.query_one.return_value = None
        assert _find_existing_resource_id(client, "result.txt", 42) is None
        client.reader.query_one.assert_called_once_with(
            "resource", {"name": "result.txt", "workunitid": 42}, expected_type=ANY
        )

    def test_returns_id_when_found(self) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import _find_existing_resource_id

        client = MagicMock()
        mock_resource = MagicMock()
        mock_resource.id = 99
        client.reader.query_one.return_value = mock_resource
        assert _find_existing_resource_id(client, "result.txt", 42) == 99


def _make_registration(
    workunit_id: int = 347246,
    storage_id: int = 5,
    storage_output_folder: str = "p123/bfabric/Genomics/MyApp/2024/2024-01/2024-01-15/workunit_347246",
) -> MagicMock:
    reg = MagicMock()
    reg.workunit_id = workunit_id
    reg.storage_id = storage_id
    reg.storage_output_folder = Path(storage_output_folder)
    return reg


class TestUploadWorkunitFolder:
    """Functional tests for upload_workunit_folder (the core logic function)."""

    @pytest.fixture
    def delivery_folder(self, tmp_path: Path) -> Path:
        (tmp_path / "result.txt").write_text("hello world")
        return tmp_path

    def _make_client(
        self, storage_base: Path, registration: MagicMock, existing_resource_id: int | None = None
    ) -> MagicMock:
        """Build a mock Bfabric client with reader.query_one routing storage vs resource lookups."""
        client = MagicMock()
        mock_storage = MagicMock()
        mock_storage.base_path = storage_base

        mock_existing = MagicMock(id=existing_resource_id) if existing_resource_id is not None else None

        def _query_one(entity_type: str, obj: object, *, expected_type: object = None) -> object:
            if entity_type == "storage":
                return mock_storage
            return mock_existing  # resource check: None → not found, MagicMock(id=...) → found

        client.reader.query_one.side_effect = _query_one
        return client

    def test_dry_run_does_not_call_save(self, delivery_folder: Path, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import upload_workunit_folder

        reg = _make_registration()
        mock_wd = MagicMock()
        mock_wd.registration = reg
        client = self._make_client(tmp_path / "storage", reg)

        with patch("bfabric_scripts.bfabric_upload_workunit_folder.WorkunitDefinition.from_ref", return_value=mock_wd):
            upload_workunit_folder(workunit_id=347246, folder=delivery_folder, execute=False, client=client)

        client.save.assert_not_called()

    def test_dry_run_does_not_write_files(self, delivery_folder: Path, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import upload_workunit_folder

        reg = _make_registration()
        mock_wd = MagicMock()
        mock_wd.registration = reg
        client = self._make_client(tmp_path / "storage", reg)

        with (
            patch("bfabric_scripts.bfabric_upload_workunit_folder.WorkunitDefinition.from_ref", return_value=mock_wd),
            patch("bfabric_scripts.bfabric_upload_workunit_folder.shutil") as mock_shutil,
        ):
            upload_workunit_folder(workunit_id=347246, folder=delivery_folder, execute=False, client=client)

        mock_shutil.copy.assert_not_called()

    def test_execute_saves_resource_with_7_required_fields(self, delivery_folder: Path, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import upload_workunit_folder

        reg = _make_registration()
        mock_wd = MagicMock()
        mock_wd.registration = reg
        client = self._make_client(tmp_path / "storage", reg)

        with patch("bfabric_scripts.bfabric_upload_workunit_folder.WorkunitDefinition.from_ref", return_value=mock_wd):
            upload_workunit_folder(workunit_id=347246, folder=delivery_folder, execute=True, client=client)

        client.save.assert_called_once()
        endpoint, resource_data = client.save.call_args.args
        assert endpoint == "resource"
        assert resource_data["name"] == "result.txt"
        assert resource_data["workunitid"] == 347246
        assert resource_data["storageid"] == 5
        assert "relativepath" in resource_data
        assert "filechecksum" in resource_data
        assert resource_data["status"] == "available"
        assert resource_data["size"] > 0
        assert "id" not in resource_data  # no pre-existing resource → no id field

    def test_execute_relativepath_contains_storage_folder_and_filename(
        self, delivery_folder: Path, tmp_path: Path
    ) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import upload_workunit_folder

        reg = _make_registration(
            storage_output_folder="p123/bfabric/Genomics/MyApp/2024/2024-01/2024-01-15/workunit_347246"
        )
        mock_wd = MagicMock()
        mock_wd.registration = reg
        client = self._make_client(tmp_path / "storage", reg)

        with patch("bfabric_scripts.bfabric_upload_workunit_folder.WorkunitDefinition.from_ref", return_value=mock_wd):
            upload_workunit_folder(workunit_id=347246, folder=delivery_folder, execute=True, client=client)

        _, resource_data = client.save.call_args.args
        rel = resource_data["relativepath"]
        assert "workunit_347246" in rel
        assert rel.endswith("result.txt")

    def test_skips_existing_resource_when_update_existing_is_false(self, delivery_folder: Path, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import upload_workunit_folder

        reg = _make_registration()
        mock_wd = MagicMock()
        mock_wd.registration = reg
        client = self._make_client(tmp_path / "storage", reg, existing_resource_id=77)

        with (
            patch("bfabric_scripts.bfabric_upload_workunit_folder.WorkunitDefinition.from_ref", return_value=mock_wd),
            patch("bfabric_scripts.bfabric_upload_workunit_folder.shutil") as mock_shutil,
        ):
            upload_workunit_folder(
                workunit_id=347246, folder=delivery_folder, execute=True, update_existing=False, client=client
            )

        client.save.assert_not_called()
        mock_shutil.copy.assert_not_called()

    def test_includes_id_when_update_existing_and_resource_exists(self, delivery_folder: Path, tmp_path: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import upload_workunit_folder

        reg = _make_registration()
        mock_wd = MagicMock()
        mock_wd.registration = reg
        client = self._make_client(tmp_path / "storage", reg, existing_resource_id=77)

        with patch("bfabric_scripts.bfabric_upload_workunit_folder.WorkunitDefinition.from_ref", return_value=mock_wd):
            upload_workunit_folder(
                workunit_id=347246, folder=delivery_folder, execute=True, update_existing=True, client=client
            )

        client.save.assert_called_once()
        _, resource_data = client.save.call_args.args
        assert resource_data["id"] == 77

    def test_raises_when_registration_is_none(self, delivery_folder: Path) -> None:
        from bfabric_scripts.bfabric_upload_workunit_folder import upload_workunit_folder

        mock_wd = MagicMock()
        mock_wd.registration = None

        with (
            patch("bfabric_scripts.bfabric_upload_workunit_folder.WorkunitDefinition.from_ref", return_value=mock_wd),
            pytest.raises(ValueError, match="no registration"),
        ):
            upload_workunit_folder(workunit_id=347246, folder=delivery_folder, execute=False, client=MagicMock())

from __future__ import annotations

from pathlib import Path

import pytest

from bfabric.transfer._generic.checksums import (
    collect_file_infos,
    compute_file_info,
    md5_checksum,
    resolve_paths,
)


def test_md5_checksum(tmp_path: Path) -> None:
    f = tmp_path / "data.bin"
    f.write_bytes(b"some bytes to hash")

    # Literal md5 of b"some bytes to hash" -- an independent oracle, not a re-run of the code.
    assert md5_checksum(f) == "03d01978f780dc8c34c0e279df48a8ce"


def test_compute_file_info_basename(tmp_path: Path) -> None:
    f = tmp_path / "hello.txt"
    f.write_bytes(b"hello world")

    fi = compute_file_info(f)

    assert fi.name == "hello.txt"
    assert fi.size == 11
    # Literal md5 of b"hello world".
    assert fi.md5 == "5eb63bbbe01eeed093cb22bb8f5acdc3"
    assert fi.path == f


def test_compute_file_info_relative_name_with_base_dir(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    f = sub / "file.txt"
    f.write_bytes(b"x")

    fi = compute_file_info(f, base_dir=tmp_path)

    assert fi.name == "sub/file.txt"


def test_resolve_paths_expands_directories_recursively(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"a")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_bytes(b"b")

    resolved = resolve_paths([tmp_path])

    names = sorted(p.name for p in resolved)
    assert names == ["a.txt", "b.txt"]


def test_resolve_paths_passes_files_through(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_bytes(b"a")

    assert resolve_paths([f]) == [f]


def test_collect_file_infos_expands_dirs_and_keeps_files(tmp_path: Path) -> None:
    (tmp_path / "top.txt").write_bytes(b"t")
    d = tmp_path / "d"
    d.mkdir()
    (d / "inner.txt").write_bytes(b"i")

    infos = collect_file_infos([tmp_path / "top.txt", d])

    # Directory expanded (relative name), plain file kept by basename.
    assert sorted(i.name for i in infos) == ["inner.txt", "top.txt"]


def test_collect_file_infos_empty_dir_raises(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    with pytest.raises(ValueError):
        collect_file_infos([empty])

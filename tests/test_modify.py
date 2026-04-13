"""Tests for image modification subcommands."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from littlefs_tools.littlefs_tools import (
    PathNotFoundError,
    do_add,
    do_create,
    do_extract,
    do_remove,
    do_rename,
    mount_image,
)


class TestDoAdd:
    def test_add_file(self, tmp_path: Path, sample_image: Path) -> None:
        new_file = tmp_path / "new.txt"
        new_file.write_bytes(b"hello world\n")
        do_add(image=str(sample_image), sources=[str(new_file)])
        fs = mount_image(str(sample_image), 4096, 64, 0)
        with fs.open("/new.txt", "rb") as fh:
            assert fh.read() == b"hello world\n"

    def test_add_to_subdir(self, tmp_path: Path, sample_image: Path) -> None:
        new_file = tmp_path / "sub.txt"
        new_file.write_bytes(b"sub content\n")
        do_add(image=str(sample_image), sources=[str(new_file)], dest="/test_dir1")
        fs = mount_image(str(sample_image), 4096, 64, 0)
        with fs.open("/test_dir1/sub.txt", "rb") as fh:
            assert fh.read() == b"sub content\n"

    def test_add_directory(self, tmp_path: Path, sample_image: Path) -> None:
        new_dir = tmp_path / "newdir"
        new_dir.mkdir()
        (new_dir / "a.txt").write_bytes(b"aaa\n")
        (new_dir / "b.txt").write_bytes(b"bbb\n")
        do_add(image=str(sample_image), sources=[str(new_dir)])
        fs = mount_image(str(sample_image), 4096, 64, 0)
        with fs.open("/a.txt", "rb") as fh:
            assert fh.read() == b"aaa\n"

    def test_add_preserves_existing(self, tmp_path: Path, sample_image: Path) -> None:
        new_file = tmp_path / "extra.txt"
        new_file.write_bytes(b"extra\n")
        do_add(image=str(sample_image), sources=[str(new_file)])
        fs = mount_image(str(sample_image), 4096, 64, 0)
        with fs.open("/test_dir1/test_dir1.txt", "rb") as fh:
            assert fh.read() == b"test_dir1\n"

    def test_add_source_not_found(self, sample_image: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Source not found"):
            do_add(image=str(sample_image), sources=["/nonexistent"])


class TestDoRemove:
    def test_remove_file(self, sample_image: Path) -> None:
        do_remove(image=str(sample_image), paths=["/test_dir1/test_dir1.txt"])
        fs = mount_image(str(sample_image), 4096, 64, 0)
        names = [e.name for e in fs.scandir("/test_dir1")]
        assert "test_dir1.txt" not in names

    def test_remove_directory_recursive(self, sample_image: Path) -> None:
        do_remove(image=str(sample_image), paths=["/test_dir1"], recursive=True)
        fs = mount_image(str(sample_image), 4096, 64, 0)
        names = [e.name for e in fs.scandir("/")]
        assert "test_dir1" not in names

    def test_remove_nonexistent(self, sample_image: Path) -> None:
        with pytest.raises(PathNotFoundError, match="Cannot remove"):
            do_remove(image=str(sample_image), paths=["/nonexistent"])

    def test_remove_preserves_others(self, sample_image: Path) -> None:
        do_remove(image=str(sample_image), paths=["/test_dir1/test_dir1.txt"])
        fs = mount_image(str(sample_image), 4096, 64, 0)
        with fs.open("/test_dir2/test_dir2.txt", "rb") as fh:
            assert fh.read() == b"test_dir2\n"


class TestDoRename:
    def test_rename_file(self, sample_image: Path) -> None:
        do_rename(image=str(sample_image), src_path="/test_dir1/test_dir1.txt", dst_path="/test_dir1/renamed.txt")
        fs = mount_image(str(sample_image), 4096, 64, 0)
        with fs.open("/test_dir1/renamed.txt", "rb") as fh:
            assert fh.read() == b"test_dir1\n"

    def test_rename_nonexistent(self, sample_image: Path) -> None:
        with pytest.raises(PathNotFoundError, match="Cannot rename"):
            do_rename(image=str(sample_image), src_path="/nonexistent", dst_path="/new")


class TestCompact:
    def test_compact_smaller_than_full(self, tmp_path: Path, sample_tree: Path) -> None:
        full_image = tmp_path / "full.bin"
        compact_image = tmp_path / "compact.bin"
        do_create(source=str(sample_tree), image=str(full_image), block_size=4096, block_count=64, offset=0)
        do_create(
            source=str(sample_tree), image=str(compact_image),
            block_size=4096, block_count=64, offset=0, compact=True,
        )
        assert compact_image.stat().st_size < full_image.stat().st_size

    def test_compact_round_trip(self, tmp_path: Path, sample_tree: Path) -> None:
        image = tmp_path / "compact.bin"
        do_create(source=str(sample_tree), image=str(image), block_size=4096, block_count=64, offset=0, compact=True)
        # Compact images are truncated; compute block_count from file size
        compact_bc = image.stat().st_size // 4096
        dest = tmp_path / "extracted"
        do_extract(image=str(image), destination=str(dest), block_size=4096, block_count=compact_bc)
        for root, _dirs, files in os.walk(sample_tree):
            for name in files:
                src_file = Path(root) / name
                rel = src_file.relative_to(sample_tree)
                dst_file = dest / rel
                assert dst_file.exists(), f"Missing: {rel}"
                assert dst_file.read_bytes() == src_file.read_bytes(), f"Mismatch: {rel}"

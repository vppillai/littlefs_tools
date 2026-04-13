"""Tests for the diff subcommand."""
from __future__ import annotations

from pathlib import Path

from littlefs_tools.littlefs_tools import do_add, do_create, do_diff, do_remove


class TestDoDiff:
    def test_identical_images(self, tmp_path: Path, sample_tree: Path) -> None:
        img1 = tmp_path / "img1.bin"
        img2 = tmp_path / "img2.bin"
        do_create(source=str(sample_tree), image=str(img1), block_size=4096, block_count=64, offset=0)
        do_create(source=str(sample_tree), image=str(img2), block_size=4096, block_count=64, offset=0)
        result = do_diff(image1=str(img1), image2=str(img2))
        assert len(result["only_in_1"]) == 0
        assert len(result["only_in_2"]) == 0
        assert len(result["different"]) == 0
        assert len(result["identical"]) > 0

    def test_added_file(self, tmp_path: Path, sample_tree: Path) -> None:
        img1 = tmp_path / "img1.bin"
        img2 = tmp_path / "img2.bin"
        do_create(source=str(sample_tree), image=str(img1), block_size=4096, block_count=64, offset=0)
        do_create(source=str(sample_tree), image=str(img2), block_size=4096, block_count=64, offset=0)
        extra = tmp_path / "extra.txt"
        extra.write_bytes(b"extra\n")
        do_add(image=str(img2), sources=[str(extra)])
        result = do_diff(image1=str(img1), image2=str(img2))
        assert "/extra.txt" in result["only_in_2"]

    def test_removed_file(self, tmp_path: Path, sample_tree: Path) -> None:
        img1 = tmp_path / "img1.bin"
        img2 = tmp_path / "img2.bin"
        do_create(source=str(sample_tree), image=str(img1), block_size=4096, block_count=64, offset=0)
        do_create(source=str(sample_tree), image=str(img2), block_size=4096, block_count=64, offset=0)
        do_remove(image=str(img2), paths=["/test_dir1/test_dir1.txt"])
        result = do_diff(image1=str(img1), image2=str(img2))
        assert "/test_dir1/test_dir1.txt" in result["only_in_1"]

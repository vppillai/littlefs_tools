"""Tests for gc, grow, repair operations."""
from __future__ import annotations

from pathlib import Path

import pytest

from littlefs_tools.littlefs_tools import (
    ValidationError,
    do_gc,
    do_grow,
    do_info,
    do_repair,
    mount_image,
)


class TestDoGc:
    def test_gc_runs(self, sample_image: Path) -> None:
        used = do_gc(image=str(sample_image))
        assert used > 0

    def test_gc_preserves_files(self, sample_image: Path) -> None:
        do_gc(image=str(sample_image))
        fs = mount_image(str(sample_image), 4096, 64, 0)
        with fs.open("/test_dir1/test_dir1.txt", "rb") as fh:
            assert fh.read() == b"test_dir1\n"


class TestDoGrow:
    def test_grow_by_block_count(self, sample_image: Path) -> None:
        do_grow(image=str(sample_image), new_block_count=128)
        info = do_info(image=str(sample_image))
        assert info["block_count"] == 128

    def test_grow_by_size(self, sample_image: Path) -> None:
        do_grow(image=str(sample_image), new_size="512kb")
        info = do_info(image=str(sample_image))
        assert info["block_count"] == 128  # 512kb / 4096 = 128

    def test_grow_preserves_files(self, sample_image: Path) -> None:
        do_grow(image=str(sample_image), new_block_count=128)
        fs = mount_image(str(sample_image), 4096, 128, 0)
        with fs.open("/test_dir1/test_dir1.txt", "rb") as fh:
            assert fh.read() == b"test_dir1\n"

    def test_grow_smaller_fails(self, sample_image: Path) -> None:
        with pytest.raises(ValidationError, match="must exceed"):
            do_grow(image=str(sample_image), new_block_count=32)


class TestDoRepair:
    def test_repair_runs(self, sample_image: Path) -> None:
        do_repair(image=str(sample_image))
        fs = mount_image(str(sample_image), 4096, 64, 0)
        with fs.open("/test_dir1/test_dir1.txt", "rb") as fh:
            assert fh.read() == b"test_dir1\n"

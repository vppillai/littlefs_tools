"""Tests for the info subcommand."""
from __future__ import annotations

from pathlib import Path

from littlefs_tools.littlefs_tools import do_info


class TestDoInfo:
    def test_basic(self, sample_image: Path) -> None:
        info = do_info(image=str(sample_image), block_size=4096, block_count=64)
        assert info["block_size"] == 4096
        assert info["block_count"] == 64
        assert info["file_count"] == 9
        assert info["dir_count"] == 9
        assert info["used_blocks"] > 0
        assert info["free_blocks"] >= 0
        assert 0 <= info["used_pct"] <= 100

    def test_auto_detect(self, sample_image: Path) -> None:
        info = do_info(image=str(sample_image))
        assert info["block_size"] == 4096
        assert info["block_count"] == 64

    def test_empty_image(self, tmp_path: Path) -> None:
        from littlefs_tools.littlefs_tools import do_create

        src = tmp_path / "empty"
        src.mkdir()
        image = tmp_path / "empty.bin"
        do_create(source=str(src), image=str(image), block_size=4096, block_count=8, offset=0)
        info = do_info(image=str(image))
        assert info["file_count"] == 0
        assert info["dir_count"] == 0

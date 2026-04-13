"""Tests for the verify subcommand."""
from __future__ import annotations

from pathlib import Path

from littlefs_tools.littlefs_tools import do_verify


class TestDoVerify:
    def test_valid_image(self, sample_image: Path) -> None:
        result = do_verify(image=str(sample_image))
        assert result["valid"] is True
        assert "superblock_magic" in result["checks_passed"]
        assert "mount" in result["checks_passed"]
        assert "file_integrity" in result["checks_passed"]
        assert len(result["errors"]) == 0

    def test_corrupt_image(self, tmp_path: Path) -> None:
        bad = tmp_path / "corrupt.bin"
        bad.write_bytes(b"\x00" * 8192)
        result = do_verify(image=str(bad))
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_auto_detect(self, sample_image: Path) -> None:
        result = do_verify(image=str(sample_image))
        assert result["valid"] is True

    def test_missing_file(self, tmp_path: Path) -> None:
        result = do_verify(image=str(tmp_path / "nope.bin"))
        assert result["valid"] is False

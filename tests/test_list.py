"""Tests for image listing functionality."""

from __future__ import annotations

from pathlib import Path

import pytest

from littlefs_tools.littlefs_tools import (
    ValidationError,
    do_list,
    sizeof_fmt,
)


class TestSizeofFmt:
    """Tests for sizeof_fmt()."""

    def test_bytes(self) -> None:
        assert sizeof_fmt(100) == "100.0 B"

    def test_kibibytes(self) -> None:
        assert sizeof_fmt(4096) == "4.0 KiB"

    def test_mebibytes(self) -> None:
        assert sizeof_fmt(1048576) == "1.0 MiB"

    def test_zero(self) -> None:
        assert sizeof_fmt(0) == "0.0 B"


class TestDoList:
    """Tests for do_list()."""

    def test_list_basic(self, sample_image: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Listing a valid image prints all expected file and directory names."""
        do_list(
            image=str(sample_image),
            block_size=4096,
            block_count=64,
            offset=0,
        )
        output = capsys.readouterr().out
        for i in range(1, 4):
            assert f"test_dir{i}" in output
            assert f"test_dir{i}.txt" in output
            for j in range(1, 3):
                assert f"test_dir{i}_{j}" in output
                assert f"test_dir{i}_{j}.txt" in output

    def test_list_file_not_found(self, tmp_path: Path) -> None:
        """Raise FileNotFoundError for a nonexistent image."""
        with pytest.raises(FileNotFoundError, match="Image file not found"):
            do_list(
                image=str(tmp_path / "nope.bin"),
                block_size=4096,
                block_count=64,
                offset=0,
            )

    def test_list_invalid_block_size(self, sample_image: Path) -> None:
        """Raise ValidationError for a non-power-of-2 block size."""
        with pytest.raises(ValidationError, match="power of 2"):
            do_list(
                image=str(sample_image),
                block_size=3000,
                block_count=64,
                offset=0,
            )

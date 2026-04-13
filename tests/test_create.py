"""Tests for image creation functionality."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from littlefs_tools.littlefs_tools import (
    ImageTooSmallError,
    ValidationError,
    do_create,
)


class TestDoCreate:
    """Tests for do_create()."""

    def test_create_basic(self, tmp_path: Path, sample_tree: Path) -> None:
        """Creating an image from a valid source directory produces a non-empty file."""
        image = tmp_path / "out.bin"
        do_create(
            source=str(sample_tree),
            image=str(image),
            block_size=4096,
            block_count=64,
            offset=0,
        )
        assert image.exists()
        assert image.stat().st_size == 4096 * 64

    def test_create_with_offset(self, tmp_path: Path, sample_tree: Path) -> None:
        """An offset prepends zero-padding to the image."""
        image = tmp_path / "out.bin"
        offset = 0x1000
        do_create(
            source=str(sample_tree),
            image=str(image),
            block_size=4096,
            block_count=64,
            offset=offset,
        )
        data = image.read_bytes()
        assert len(data) == (4096 * 64) + offset
        assert data[:offset] == b"\x00" * offset

    def test_create_source_not_found(self, tmp_path: Path) -> None:
        """Raise FileNotFoundError when source directory does not exist."""
        with pytest.raises(FileNotFoundError, match="Source directory not found"):
            do_create(
                source=str(tmp_path / "nonexistent"),
                image=str(tmp_path / "out.bin"),
                block_size=4096,
                block_count=64,
                offset=0,
            )

    def test_create_invalid_block_size(self, tmp_path: Path, sample_tree: Path) -> None:
        """Raise ValidationError for a non-power-of-2 block size."""
        with pytest.raises(ValidationError, match="power of 2"):
            do_create(
                source=str(sample_tree),
                image=str(tmp_path / "out.bin"),
                block_size=1000,
                block_count=64,
                offset=0,
            )

    def test_create_invalid_block_count(self, tmp_path: Path, sample_tree: Path) -> None:
        """Raise ValidationError for zero or negative block count."""
        with pytest.raises(ValidationError, match="positive integer"):
            do_create(
                source=str(sample_tree),
                image=str(tmp_path / "out.bin"),
                block_size=4096,
                block_count=0,
                offset=0,
            )

    def test_create_image_too_small(self, tmp_path: Path) -> None:
        """Raise ImageTooSmallError when contents exceed capacity."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "big.bin").write_bytes(b"\xff" * 2000)
        with pytest.raises(ImageTooSmallError, match="exceed image capacity"):
            do_create(
                source=str(src),
                image=str(tmp_path / "out.bin"),
                block_size=512,
                block_count=4,
                offset=0,
            )

    def test_create_empty_directory(self, tmp_path: Path) -> None:
        """Creating from an empty directory produces a valid image."""
        src = tmp_path / "empty"
        src.mkdir()
        image = tmp_path / "out.bin"
        do_create(
            source=str(src),
            image=str(image),
            block_size=4096,
            block_count=8,
            offset=0,
        )
        assert image.exists()
        assert image.stat().st_size == 4096 * 8

    def test_create_custom_name_max(self, tmp_path: Path, sample_tree: Path) -> None:
        """Creating with custom name_max propagates the setting."""
        image = tmp_path / "out.bin"
        do_create(
            source=str(sample_tree),
            image=str(image),
            block_size=4096,
            block_count=64,
            offset=0,
            name_max=64,
        )
        from littlefs_tools.littlefs_tools import do_info

        info = do_info(image=str(image))
        assert info["name_max"] == 64


class TestRoundTrip:
    """End-to-end: create -> extract -> compare."""

    def test_round_trip(self, tmp_path: Path, sample_tree: Path) -> None:
        """Files survive a create->extract round trip unchanged."""
        from littlefs_tools.littlefs_tools import do_extract

        image = tmp_path / "round.bin"
        dest = tmp_path / "extracted"
        do_create(
            source=str(sample_tree),
            image=str(image),
            block_size=4096,
            block_count=64,
            offset=0,
        )
        do_extract(
            image=str(image),
            block_size=4096,
            block_count=64,
            offset=0,
            destination=str(dest),
        )
        for root, _dirs, files in os.walk(sample_tree):
            for name in files:
                src_file = Path(root) / name
                rel = src_file.relative_to(sample_tree)
                dst_file = dest / rel
                assert dst_file.exists(), f"Missing: {rel}"
                assert dst_file.read_bytes() == src_file.read_bytes(), f"Mismatch: {rel}"

    def test_round_trip_with_offset(self, tmp_path: Path, sample_tree: Path) -> None:
        """Round trip works with a non-zero offset."""
        from littlefs_tools.littlefs_tools import do_extract

        image = tmp_path / "offset.bin"
        dest = tmp_path / "extracted"
        offset = 0x8000
        do_create(
            source=str(sample_tree),
            image=str(image),
            block_size=4096,
            block_count=64,
            offset=offset,
        )
        do_extract(
            image=str(image),
            block_size=4096,
            block_count=64,
            offset=offset,
            destination=str(dest),
        )
        for root, _dirs, files in os.walk(sample_tree):
            for name in files:
                src_file = Path(root) / name
                rel = src_file.relative_to(sample_tree)
                dst_file = dest / rel
                assert dst_file.exists(), f"Missing: {rel}"
                assert dst_file.read_bytes() == src_file.read_bytes(), f"Mismatch: {rel}"

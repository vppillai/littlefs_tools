"""Tests for image extraction functionality."""

from __future__ import annotations

from pathlib import Path

import pytest

from littlefs_tools.littlefs_tools import (
    DestinationNotEmptyError,
    ValidationError,
    do_extract,
)


class TestDoExtract:
    """Tests for do_extract()."""

    def test_extract_basic(self, tmp_path: Path, sample_image: Path) -> None:
        """Extracting produces the expected directory structure."""
        dest = tmp_path / "out"
        do_extract(
            image=str(sample_image),
            block_size=4096,
            block_count=64,
            offset=0,
            destination=str(dest),
        )
        assert dest.exists()
        f = dest / "test_dir1" / "test_dir1.txt"
        assert f.exists()
        assert f.read_text() == "test_dir1\n"

    def test_extract_destination_not_empty(self, tmp_path: Path, sample_image: Path) -> None:
        """Raise DestinationNotEmptyError when dest is not empty and force=False."""
        dest = tmp_path / "out"
        dest.mkdir()
        (dest / "existing.txt").write_text("data")
        with pytest.raises(DestinationNotEmptyError, match="not empty"):
            do_extract(
                image=str(sample_image),
                block_size=4096,
                block_count=64,
                offset=0,
                destination=str(dest),
            )

    def test_extract_force_overwrites(self, tmp_path: Path, sample_image: Path) -> None:
        """With force=True, extraction succeeds even if dest is non-empty."""
        dest = tmp_path / "out"
        dest.mkdir()
        (dest / "existing.txt").write_text("data")
        do_extract(
            image=str(sample_image),
            block_size=4096,
            block_count=64,
            offset=0,
            destination=str(dest),
            force=True,
        )
        assert (dest / "test_dir1" / "test_dir1.txt").exists()

    def test_extract_image_not_found(self, tmp_path: Path) -> None:
        """Raise FileNotFoundError for a nonexistent image."""
        with pytest.raises(FileNotFoundError, match="Image file not found"):
            do_extract(
                image=str(tmp_path / "nope.bin"),
                block_size=4096,
                block_count=64,
                offset=0,
                destination=str(tmp_path / "out"),
            )

    def test_extract_invalid_block_count(self, tmp_path: Path, sample_image: Path) -> None:
        """Raise ValidationError for negative block count."""
        with pytest.raises(ValidationError, match="positive integer"):
            do_extract(
                image=str(sample_image),
                block_size=4096,
                block_count=-1,
                offset=0,
                destination=str(tmp_path / "out"),
            )

    def test_extract_specific_file(self, tmp_path: Path, sample_image: Path) -> None:
        """Extract only specific file paths."""
        dest = tmp_path / "out"
        do_extract(
            image=str(sample_image),
            destination=str(dest),
            paths=["/test_dir1/test_dir1.txt"],
        )
        assert (dest / "test_dir1" / "test_dir1.txt").exists()
        # Files in other directories should not be extracted
        assert not (dest / "test_dir2" / "test_dir2.txt").exists()
        assert not (dest / "test_dir3" / "test_dir3.txt").exists()

    def test_extract_pattern(self, tmp_path: Path, sample_image: Path) -> None:
        """Extract only files matching a glob pattern."""
        dest = tmp_path / "out"
        do_extract(
            image=str(sample_image),
            destination=str(dest),
            pattern="test_dir1.txt",
        )
        assert (dest / "test_dir1" / "test_dir1.txt").exists()

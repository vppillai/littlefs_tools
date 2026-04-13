"""Tests for the cat subcommand."""
from __future__ import annotations

from pathlib import Path

import pytest

from littlefs_tools.littlefs_tools import PathNotFoundError, do_cat


class TestDoCat:
    def test_text_file(self, sample_image: Path) -> None:
        data = do_cat(image=str(sample_image), path="/test_dir1/test_dir1.txt")
        assert data == b"test_dir1\n"

    def test_nested_file(self, sample_image: Path) -> None:
        data = do_cat(image=str(sample_image), path="/test_dir2/test_dir2_1/test_dir2_1.txt")
        assert data == b"test_dir2_1\n"

    def test_auto_detect(self, sample_image: Path) -> None:
        data = do_cat(image=str(sample_image), path="/test_dir1/test_dir1.txt")
        assert b"test_dir1" in data

    def test_file_not_found(self, sample_image: Path) -> None:
        with pytest.raises(PathNotFoundError, match="File not found"):
            do_cat(image=str(sample_image), path="/nonexistent.txt")

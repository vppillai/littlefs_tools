"""Tests for extended attribute operations."""
from __future__ import annotations

from pathlib import Path

import pytest

from littlefs_tools.littlefs_tools import PathNotFoundError, do_getattr, do_removeattr, do_setattr


class TestExtendedAttributes:
    def test_set_and_get(self, sample_image: Path) -> None:
        do_setattr(image=str(sample_image), path="/test_dir1/test_dir1.txt", attr_type=0x42, data=b"hello")
        result = do_getattr(image=str(sample_image), path="/test_dir1/test_dir1.txt", attr_type=0x42)
        assert result == b"hello"

    def test_remove_attr(self, sample_image: Path) -> None:
        do_setattr(image=str(sample_image), path="/test_dir1/test_dir1.txt", attr_type=0x10, data=b"test")
        do_removeattr(image=str(sample_image), path="/test_dir1/test_dir1.txt", attr_type=0x10)
        with pytest.raises(PathNotFoundError):
            do_getattr(image=str(sample_image), path="/test_dir1/test_dir1.txt", attr_type=0x10)

    def test_get_nonexistent(self, sample_image: Path) -> None:
        with pytest.raises(PathNotFoundError):
            do_getattr(image=str(sample_image), path="/test_dir1/test_dir1.txt", attr_type=0xFF)

"""Shared pytest fixtures for littlefs_tools tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def sample_tree(tmp_path: Path) -> Path:
    """Create a sample directory tree matching the structure used by test.sh."""
    src = tmp_path / "testSource"
    for i in range(1, 4):
        d = src / f"test_dir{i}"
        d.mkdir(parents=True)
        (d / f"test_dir{i}.txt").write_bytes(f"test_dir{i}\n".encode())
        for j in range(1, 3):
            sd = d / f"test_dir{i}_{j}"
            sd.mkdir()
            (sd / f"test_dir{i}_{j}.txt").write_bytes(f"test_dir{i}_{j}\n".encode())
    return src


@pytest.fixture()
def sample_image(tmp_path: Path, sample_tree: Path) -> Path:
    """Create a littleFS image from sample_tree and return its path."""
    from littlefs_tools.littlefs_tools import do_create

    image_path = tmp_path / "test.bin"
    do_create(
        source=str(sample_tree),
        image=str(image_path),
        block_size=4096,
        block_count=64,
        offset=0,
    )
    return image_path

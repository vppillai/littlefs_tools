"""Tests for the du subcommand."""
from __future__ import annotations

from pathlib import Path

from littlefs_tools.littlefs_tools import do_du


class TestDoDu:
    def test_basic(self, sample_image: Path) -> None:
        results = do_du(image=str(sample_image))
        assert len(results) > 0
        root = next(r for r in results if r["path"] == "/")
        assert root["files"] >= 0
        assert root["dirs"] >= 0

    def test_total_bytes(self, sample_image: Path) -> None:
        results = do_du(image=str(sample_image))
        total = sum(r["bytes"] for r in results)
        assert total > 0

    def test_auto_detect(self, sample_image: Path) -> None:
        results = do_du(image=str(sample_image))
        assert len(results) > 0
